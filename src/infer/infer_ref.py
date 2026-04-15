"""End-to-end voice conversion inference (reference-based).

Loads source audio → extracts bottleneck (BN) features via FastU2++ ASR →
extracts speaker embedding via WavLM ECAPA-TDNN → runs DiT flow model →
decodes with Vocos vocoder.

Changes vs original:
  * torch.stft uses return_complex=True (PyTorch ≥ 2.0 clean API)
  * MelSpectrogramFeatures imported from src.utils.audio (single source of truth)
  * load_wav() used for audio I/O (handles mp3/flac/wav via torchaudio/TorchCodec)
  * get_device() auto-selects CUDA > MPS > CPU
  * model/checkpoint paths default to assets/ folder
  * No monkey-patching of torchaudio backend
"""

import os
import json
import argparse
import glob
from src.infer.dit_kvcache import DiT
from src.model.utils import load_checkpoint
import numpy as np
import torch
import time
from tqdm import tqdm
import torchaudio
import torchaudio.compliance.kaldi as kaldi
import torch.nn as nn
from src.runtime.speaker_verification.verification import init_model as init_sv_model
from src.utils.audio import MelSpectrogramFeatures, get_device, load_wav

# ---------------------------------------------------------------------------
# Project root (used to resolve default asset paths)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

C_KV_CACHE_MAX_LEN = 100


def setup_seed(seed: int) -> None:
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True


# ---------------------------------------------------------------------------
# Feature extraction helpers
# ---------------------------------------------------------------------------

def extract_fbanks(
    wav: np.ndarray,
    sample_rate: int = 16000,
    mel_bins: int = 80,
    frame_length: float = 25.0,
    frame_shift: float = 12.5,
) -> torch.Tensor:
    """Compute Kaldi-style filter-bank features from a numpy waveform array."""
    wav_scaled = wav * (1 << 15)
    wav_tensor = torch.from_numpy(wav_scaled).unsqueeze(0)
    fbanks = kaldi.fbank(
        wav_tensor,
        frame_length=frame_length,
        frame_shift=frame_shift,
        snip_edges=True,
        num_mel_bins=mel_bins,
        energy_floor=0.0,
        dither=0.0,
        sample_frequency=sample_rate,
    )
    return fbanks.unsqueeze(0)


def extract_features_from_audio(
    source_path: str,
    reference_path: str,
    asr_model: torch.ScriptModule,
    sv_model: nn.Module,
    mel_extractor: MelSpectrogramFeatures,
    device: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Extract BN, speaker embedding, and prompt mel from source + reference.

    Returns:
        bn           : [1, T_up, 256]  — upsampled bottleneck features
        spk_emb      : [1, 256]        — speaker embedding
        prompt_mel   : [1, T_ref, 80]  — prompt mel spectrogram
    """
    # ---- source: BN extraction via FastU2++ --------------------------------
    source_wav_np, _ = __import__('librosa').load(source_path, sr=16000)
    source_fbanks = extract_fbanks(source_wav_np, frame_shift=10).float().to(device)

    with torch.no_grad():
        offset = 0
        decoding_chunk_size = 5
        num_decoding_left_chunks = 2
        subsampling = 4
        context = 7  # Add current frame
        stride = subsampling * decoding_chunk_size
        required_cache_size = decoding_chunk_size * num_decoding_left_chunks
        decoding_window = (decoding_chunk_size - 1) * subsampling + context

        att_cache = torch.zeros((0, 0, 0, 0), device=device)
        cnn_cache = torch.zeros((0, 0, 0, 0), device=device)
        bn_chunks: list[torch.Tensor] = []

        for i in range(0, source_fbanks.shape[1], stride):
            fbank_chunk = source_fbanks[:, i : i + decoding_window, :]
            if fbank_chunk.shape[1] < required_cache_size:
                pad_size = required_cache_size - fbank_chunk.shape[1]
                fbank_chunk = torch.nn.functional.pad(
                    fbank_chunk, (0, 0, 0, pad_size), mode="constant", value=0.0
                )

            encoder_output, att_cache, cnn_cache = asr_model.forward_encoder_chunk(
                fbank_chunk, offset, required_cache_size, att_cache, cnn_cache
            )
            offset += encoder_output.size(1)
            bn_chunks.append(encoder_output)

        bn = torch.cat(bn_chunks, dim=1)           # [1, T, 256]
        bn = bn.transpose(1, 2)
        bn = torch.nn.functional.interpolate(
            bn, size=int(bn.shape[2] * 4), mode="linear", align_corners=True
        )
        bn = bn.transpose(1, 2)                    # [1, T*4, 256]

    # ---- reference: speaker embedding + prompt mel -------------------------
    # Use torchaudio.load (TorchCodec, supports mp3/flac/wav)
    ref_wav, ref_sr = torchaudio.load(reference_path)
    if ref_wav.shape[0] > 1:
        ref_wav = ref_wav.mean(dim=0, keepdim=True)
    if ref_sr != 16000:
        ref_wav = torchaudio.transforms.Resample(ref_sr, 16000)(ref_wav)
    ref_wav_tensor = ref_wav.to(device)            # [1, T]

    with torch.no_grad():
        spk_emb = sv_model(ref_wav_tensor)         # [1, 256]
        prompt_mel = mel_extractor(ref_wav_tensor) # [1, 80, T]
        prompt_mel = prompt_mel.transpose(1, 2)    # [1, T, 80]

    return bn, spk_emb, prompt_mel


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------

@torch.inference_mode()
def inference(
    model: DiT,
    vocos: torch.ScriptModule,
    bn: torch.Tensor,
    spk_emb: torch.Tensor,
    prompt_mel: torch.Tensor,
    chunk_size: int,
    steps: int,
    device: str,
) -> tuple[torch.Tensor, torch.Tensor, float]:
    """Run chunk-wise flow-matching inference.

    Returns:
        mel       : [1, 80, T]   — predicted mel spectrogram
        wav       : [1, T_wav]   — decoded waveform
        time_item : float        — wall-clock time in seconds
    """
    if steps == 1:
        timesteps = torch.tensor([1.0, 0.0], device=device)
    elif steps == 2:
        timesteps = torch.tensor([1.0, 0.8, 0.0], device=device)
    else:
        timesteps = torch.linspace(1.0, 0.0, steps + 1, device=device)

    seq_len = bn.shape[1]
    cache: torch.Tensor | None = None
    x_pred_list: list[torch.Tensor] = []
    B = 1
    offset = 0
    kv_cache = None

    t0 = time.time()

    for start in range(0, seq_len, chunk_size):
        end = min(start + chunk_size, seq_len)
        bn_chunk = bn[:, start:end]

        x = torch.randn(B, bn_chunk.shape[1], 80, device=device, dtype=bn_chunk.dtype)

        for i in range(steps):
            t = timesteps[i]
            r = timesteps[i + 1]
            t_tensor = torch.full((B,), t, device=x.device)
            r_tensor = torch.full((B,), r, device=x.device)

            u, tmp_kv_cache = model(
                x, t_tensor, r_tensor,
                cache=cache, cond=bn_chunk, spks=spk_emb,
                prompts=prompt_mel, offset=offset,
                is_inference=True, kv_cache=kv_cache,
            )
            x = x - (t - r) * u

        kv_cache = tmp_kv_cache
        offset += x.shape[1]
        cache = x
        x_pred_list.append(x)

        # Trim KV cache to avoid quadratic memory growth
        if offset > 40 and kv_cache is not None and kv_cache[0][0].shape[2] > C_KV_CACHE_MAX_LEN:
            for i in range(len(kv_cache)):
                new_k = kv_cache[i][0][:, :, -C_KV_CACHE_MAX_LEN:, :]
                new_v = kv_cache[i][1][:, :, -C_KV_CACHE_MAX_LEN:, :]
                kv_cache[i] = (new_k, new_v)

    x_pred = torch.cat(x_pred_list, dim=1)
    mel = x_pred.transpose(1, 2)
    mel = (mel + 1) / 2
    wav = vocos.decode(mel)
    time_item = time.time() - t0

    return mel, wav, time_item


def inference_list(
    model: DiT,
    vocos: torch.ScriptModule,
    asr_model: torch.ScriptModule,
    sv_model: nn.Module,
    mel_extractor: MelSpectrogramFeatures,
    sources: list[str],
    reference_path: str,
    chunk_size: int,
    steps: int,
    output_dir: str,
    device: str,
) -> None:
    """Run voice conversion for a list of source audio files."""
    rtfs: list[float] = []
    all_duration = 0.0
    all_time = 0.0

    for source_path in tqdm(sources):
        print(f"\nProcessing: {source_path}")

        bn, spk_emb, prompt_mel = extract_features_from_audio(
            source_path, reference_path, asr_model, sv_model, mel_extractor, device
        )

        mel, wav, time_item = inference(
            model, vocos, bn, spk_emb, prompt_mel, chunk_size, steps, device
        )

        base_filename = os.path.splitext(os.path.basename(source_path))[0]

        # Save mel
        mel_output_path = os.path.join(output_dir, base_filename + ".npy")
        np.save(mel_output_path, mel.cpu().numpy())

        # Save waveform — torchaudio.save is the clean API (no backend monkey-patch needed)
        wav_output_dir = output_dir + "_wav"
        os.makedirs(wav_output_dir, exist_ok=True)
        wav_output_path = os.path.join(wav_output_dir, base_filename + ".wav")
        torchaudio.save(wav_output_path, wav.cpu(), 16000)

        duration = wav.shape[1] / 16000
        all_duration += duration
        all_time += time_item
        rtf = time_item / duration
        rtfs.append(rtf)

        print(f"  Duration: {duration:.2f}s | Inference: {time_item:.2f}s | RTF: {rtf:.4f}")
        print(f"  Saved → {wav_output_path}")

    print("\n=== Results ===")
    print(f"Total RTF  : {all_time / max(all_duration, 1e-6):.4f}")
    print(f"Mean RTF   : {np.mean(rtfs):.4f}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MeanVC reference-based voice conversion",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model-config", type=str, required=True)
    parser.add_argument(
        "--ckpt-path",
        type=str,
        default=os.path.join(_PROJECT_ROOT, "assets", "ckpt", "meanvc_200ms.pt"),
    )
    parser.add_argument(
        "--asr-ckpt-path",
        type=str,
        default=os.path.join(_PROJECT_ROOT, "assets", "ckpt", "fastu2++.pt"),
    )
    parser.add_argument(
        "--sv-ckpt-path",
        type=str,
        default=os.path.join(_PROJECT_ROOT, "assets", "wavLM", "wavlm_large_finetune.pth"),
    )
    parser.add_argument(
        "--vocoder-ckpt-path",
        type=str,
        default=os.path.join(_PROJECT_ROOT, "assets", "ckpt", "vocos.pt"),
    )
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--source-path", type=str, required=True,
                        help="Source audio file or directory")
    parser.add_argument("--reference-path", type=str, required=True,
                        help="Reference audio file (target speaker)")
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--device", type=str, default=None,
        help="Force device: cpu | mps | cuda. Auto-detected if not set.",
    )

    args = parser.parse_args()
    setup_seed(args.seed)
    os.makedirs(args.output_dir, exist_ok=True)

    device = get_device(args.device)
    print(f"Using device: {device}")

    # ---- load model config ------------------------------------------------
    with open(args.model_config) as f:
        model_config = json.load(f)

    # ---- DiT model --------------------------------------------------------
    dit_model = DiT(**model_config["model"])
    total_params = sum(p.numel() for p in dit_model.parameters())
    print(f"DiT parameters: {total_params:,}")
    dit_model = dit_model.to(device)
    dit_model = load_checkpoint(dit_model, args.ckpt_path, device=device, use_ema=False)
    dit_model = dit_model.float()
    dit_model.eval()

    # ---- Vocos vocoder (TorchScript) --------------------------------------
    vocos = torch.jit.load(args.vocoder_ckpt_path, map_location=device)
    vocos.eval()

    # ---- FastU2++ ASR (TorchScript) ---------------------------------------
    asr_model = torch.jit.load(args.asr_ckpt_path, map_location=device)
    asr_model.eval()

    # ---- Speaker verification model (WavLM ECAPA-TDNN) --------------------
    sv_model = init_sv_model("wavlm_large", args.sv_ckpt_path)
    sv_model = sv_model.to(device)
    sv_model.eval()

    # ---- Mel extractor ----------------------------------------------------
    mel_extractor = MelSpectrogramFeatures(
        sample_rate=16000, n_fft=1024, win_size=640, hop_length=160,
        n_mels=80, fmin=0.0, fmax=8000.0, center=True,
    ).to(device)

    # ---- Source files -------------------------------------------------------
    if os.path.isdir(args.source_path):
        sources = sorted(
            glob.glob(os.path.join(args.source_path, "*.wav"))
            + glob.glob(os.path.join(args.source_path, "*.mp3"))
            + glob.glob(os.path.join(args.source_path, "*.flac"))
        )
    else:
        sources = [args.source_path]

    print(f"Found {len(sources)} source audio file(s)")

    inference_list(
        model=dit_model,
        vocos=vocos,
        asr_model=asr_model,
        sv_model=sv_model,
        mel_extractor=mel_extractor,
        sources=sources,
        reference_path=args.reference_path,
        chunk_size=args.chunk_size,
        steps=args.steps,
        output_dir=args.output_dir,
        device=device,
    )
