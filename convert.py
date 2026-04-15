#!/usr/bin/env python3
"""MeanVC — End-to-end voice conversion script.

Converts one or more source audio files to the target speaker's voice.

Quick usage::

    python convert.py --source ~/Documents/audio/anchor.mp3 \
                      --reference ~/Documents/audio/trump.mp3 \
                      --output /tmp/converted/

    # Convert all files in a directory
    python convert.py --source ~/Documents/audio/ \
                      --reference ~/Documents/audio/trump.mp3 \
                      --output /tmp/converted/ --steps 2

    # Force a specific device
    python convert.py --source ... --reference ... --output ... --device cpu

Device auto-selection: CUDA > MPS > CPU.
All checkpoint paths default to assets/.

Changes / design notes:
  * Single-file entry point — no preprocessing or intermediate files needed
  * Uses torchaudio.load (TorchCodec, ≥ 2.9) for mp3/flac/wav/m4a support
  * MelSpectrogramFeatures with return_complex=True (PyTorch ≥ 2.0 clean API)
  * No torchaudio backend monkey-patching
  * WavLM ECAPA-TDNN via HuggingFace transformers (no s3prl)
  * get_device() auto-selects best available device
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import torch
import torchaudio
import torchaudio.compliance.kaldi as kaldi
from tqdm import tqdm

# Ensure project root is on path
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from src.infer.dit_kvcache import DiT
from src.model.utils import load_checkpoint
from src.runtime.speaker_verification.verification import init_model as init_sv_model
from src.utils.audio import MelSpectrogramFeatures, get_device, load_wav

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

_ASSETS = os.path.join(_HERE, "assets")

DEFAULT_MODEL_CONFIG   = os.path.join(_HERE, "src", "config", "config_200ms.json")
DEFAULT_DIT_CKPT       = os.path.join(_ASSETS, "ckpt", "model_200ms.safetensors")
DEFAULT_VOCOS_CKPT     = os.path.join(_ASSETS, "ckpt", "vocos.pt")
DEFAULT_ASR_CKPT       = os.path.join(_ASSETS, "ckpt", "fastu2++.pt")
DEFAULT_SV_CKPT        = os.path.join(_ASSETS, "wavLM", "wavlm_large_finetune.pth")

C_KV_CACHE_MAX_LEN = 100


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def extract_fbanks(
    wav_np: np.ndarray,
    sample_rate: int = 16000,
    mel_bins: int = 80,
    frame_length: float = 25.0,
    frame_shift: float = 12.5,
) -> torch.Tensor:
    """Compute Kaldi filter-bank features from a float32 numpy array."""
    wav_scaled = wav_np * (1 << 15)
    wav_t = torch.from_numpy(wav_scaled).unsqueeze(0)
    fbanks = kaldi.fbank(
        wav_t,
        frame_length=frame_length,
        frame_shift=frame_shift,
        snip_edges=True,
        num_mel_bins=mel_bins,
        energy_floor=0.0,
        dither=0.0,
        sample_frequency=sample_rate,
    )
    return fbanks.unsqueeze(0)


def extract_bn(
    source_path: str,
    asr_model: torch.ScriptModule,
    device: str,
) -> torch.Tensor:
    """Extract upsampled bottleneck features from a source audio file.

    Returns:
        Tensor of shape [1, T_up, 256].
    """
    import librosa
    wav_np, _ = librosa.load(source_path, sr=16000)
    fbanks = extract_fbanks(wav_np, frame_shift=10).float().to(device)

    decoding_chunk_size = 5
    num_decoding_left_chunks = 2
    subsampling = 4
    context = 7
    stride = subsampling * decoding_chunk_size
    required_cache_size = decoding_chunk_size * num_decoding_left_chunks
    decoding_window = (decoding_chunk_size - 1) * subsampling + context

    att_cache = torch.zeros((0, 0, 0, 0), device=device)
    cnn_cache = torch.zeros((0, 0, 0, 0), device=device)
    bn_chunks: list[torch.Tensor] = []
    offset = 0

    with torch.no_grad():
        for i in range(0, fbanks.shape[1], stride):
            chunk = fbanks[:, i : i + decoding_window, :]
            if chunk.shape[1] < required_cache_size:
                pad = required_cache_size - chunk.shape[1]
                chunk = torch.nn.functional.pad(
                    chunk, (0, 0, 0, pad), mode="constant", value=0.0
                )
            enc_out, att_cache, cnn_cache = asr_model.forward_encoder_chunk(
                chunk, offset, required_cache_size, att_cache, cnn_cache
            )
            offset += enc_out.size(1)
            bn_chunks.append(enc_out)

    bn = torch.cat(bn_chunks, dim=1)                  # [1, T, 256]
    bn = bn.transpose(1, 2)
    bn = torch.nn.functional.interpolate(
        bn, size=int(bn.shape[2] * 4), mode="linear", align_corners=True
    )
    bn = bn.transpose(1, 2)                            # [1, T*4, 256]
    return bn


def extract_speaker_and_prompt(
    reference_path: str,
    sv_model: torch.nn.Module,
    mel_extractor: MelSpectrogramFeatures,
    device: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Extract speaker embedding and prompt mel from a reference audio.

    Returns:
        spk_emb    : [1, 256]
        prompt_mel : [1, T_ref, 80]
    """
    wav, sr = torchaudio.load(reference_path)           # TorchCodec: mp3/wav/flac
    if wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)
    if sr != 16000:
        wav = torchaudio.transforms.Resample(sr, 16000)(wav)

    # WavLM-Large uses a full O(T²) relative attention bias matrix.
    # A long reference (e.g. 18-min file) would require ~180 GB for that
    # matrix alone.  Speaker identity stabilises within the first few
    # seconds so we cap the SV input at SV_MAX_SECS (10s default).
    SV_MAX_SECS = 10
    max_samples = SV_MAX_SECS * 16000
    sv_wav = wav[:, :max_samples] if wav.shape[1] > max_samples else wav

    # Also cap the prompt mel used for DiT conditioning.
    # The model uses this as style context; a few seconds is sufficient.
    # 100 mel frames ≈ 1 second at 10ms hop, so 500 frames = 5s.
    PROMPT_MAX_FRAMES = 500
    prompt_wav = wav[:, :PROMPT_MAX_FRAMES * 160] if wav.shape[1] > PROMPT_MAX_FRAMES * 160 else wav

    sv_wav = sv_wav.to(device)
    prompt_wav = prompt_wav.to(device)

    with torch.no_grad():
        spk_emb = sv_model(sv_wav)                      # [1, 256]
        prompt_mel = mel_extractor(prompt_wav)          # [1, 80, T≤500]
        prompt_mel = prompt_mel.transpose(1, 2)         # [1, T, 80]

    return spk_emb, prompt_mel


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

@torch.inference_mode()
def run_inference(
    dit_model: DiT,
    vocos: torch.ScriptModule,
    bn: torch.Tensor,
    spk_emb: torch.Tensor,
    prompt_mel: torch.Tensor,
    chunk_size: int,
    steps: int,
    device: str,
) -> tuple[torch.Tensor, torch.Tensor, float]:
    """Chunked flow-matching inference.

    Returns:
        mel       : [1, 80, T]
        wav       : [1, T_wav]
        elapsed   : float seconds
    """
    if steps == 1:
        timesteps = torch.tensor([1.0, 0.0], device=device)
    elif steps == 2:
        timesteps = torch.tensor([1.0, 0.8, 0.0], device=device)
    else:
        timesteps = torch.linspace(1.0, 0.0, steps + 1, device=device)

    seq_len = bn.shape[1]
    cache: torch.Tensor | None = None
    x_parts: list[torch.Tensor] = []
    offset = 0
    kv_cache = None
    B = 1

    t0 = time.time()

    for start in range(0, seq_len, chunk_size):
        end = min(start + chunk_size, seq_len)
        bn_chunk = bn[:, start:end]

        x = torch.randn(B, bn_chunk.shape[1], 80, device=device, dtype=bn_chunk.dtype)

        for i in range(steps):
            t = timesteps[i]
            r = timesteps[i + 1]
            t_t = torch.full((B,), t, device=device)
            r_t = torch.full((B,), r, device=device)
            u, tmp_kv = dit_model(
                x, t_t, r_t,
                cache=cache, cond=bn_chunk, spks=spk_emb,
                prompts=prompt_mel, offset=offset,
                is_inference=True, kv_cache=kv_cache,
            )
            x = x - (t - r) * u

        kv_cache = tmp_kv
        offset += x.shape[1]
        cache = x
        x_parts.append(x)

        if offset > 40 and kv_cache is not None and kv_cache[0][0].shape[2] > C_KV_CACHE_MAX_LEN:
            for i in range(len(kv_cache)):
                kv_cache[i] = (
                    kv_cache[i][0][:, :, -C_KV_CACHE_MAX_LEN:, :],
                    kv_cache[i][1][:, :, -C_KV_CACHE_MAX_LEN:, :],
                )

    mel = torch.cat(x_parts, dim=1).transpose(1, 2)    # [1, 80, T]
    mel = (mel + 1) / 2
    wav = vocos.decode(mel)                              # [1, T_wav]
    return mel, wav, time.time() - t0


# ---------------------------------------------------------------------------
# Main conversion loop
# ---------------------------------------------------------------------------

def convert(
    sources: list[str],
    reference_path: str,
    output_dir: str,
    dit_model: DiT,
    vocos: torch.ScriptModule,
    asr_model: torch.ScriptModule,
    sv_model: torch.nn.Module,
    mel_extractor: MelSpectrogramFeatures,
    chunk_size: int,
    steps: int,
    device: str,
) -> None:
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nExtracting reference speaker from: {reference_path}")
    spk_emb, prompt_mel = extract_speaker_and_prompt(
        reference_path, sv_model, mel_extractor, device
    )
    print(f"  Speaker emb shape : {spk_emb.shape}")
    print(f"  Prompt mel shape  : {prompt_mel.shape}")

    rtfs: list[float] = []

    for src in tqdm(sources, desc="Converting"):
        stem = os.path.splitext(os.path.basename(src))[0]
        out_wav = os.path.join(output_dir, stem + "_converted.wav")

        print(f"\n→ {src}")

        # BN extraction
        bn = extract_bn(src, asr_model, device)

        # Flow-matching inference
        mel, wav, elapsed = run_inference(
            dit_model, vocos, bn, spk_emb, prompt_mel,
            chunk_size=chunk_size, steps=steps, device=device,
        )

        duration = wav.shape[1] / 16000
        rtf = elapsed / max(duration, 1e-6)
        rtfs.append(rtf)

        # Save output — torchaudio.save uses TorchCodec (no backend patching)
        torchaudio.save(out_wav, wav.cpu(), 16000)
        print(f"  ✓ {out_wav}")
        print(f"    Duration={duration:.2f}s  Inference={elapsed:.2f}s  RTF={rtf:.4f}")

    if rtfs:
        print(f"\n{'='*50}")
        print(f"Converted {len(sources)} file(s) → {output_dir}")
        print(f"Mean RTF: {np.mean(rtfs):.4f}  (< 1.0 = real-time capable)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _collect_sources(source: str) -> list[str]:
    """Expand source argument to a sorted list of audio file paths."""
    if os.path.isdir(source):
        exts = ("*.wav", "*.mp3", "*.flac", "*.m4a", "*.ogg")
        files: list[str] = []
        for ext in exts:
            files.extend(glob.glob(os.path.join(source, ext)))
        return sorted(files)
    elif os.path.isfile(source):
        return [source]
    else:
        # Glob pattern
        matched = sorted(glob.glob(source))
        if not matched:
            raise FileNotFoundError(f"No files found matching: {source}")
        return matched


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MeanVC — voice conversion",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source", required=True,
        help="Source audio file, directory, or glob pattern",
    )
    parser.add_argument(
        "--reference", required=True,
        help="Reference (target speaker) audio file",
    )
    parser.add_argument(
        "--output", required=True,
        help="Output directory for converted audio",
    )
    parser.add_argument(
        "--model-config", default=DEFAULT_MODEL_CONFIG,
        help="Path to DiT model config JSON",
    )
    parser.add_argument("--dit-ckpt",   default=DEFAULT_DIT_CKPT)
    parser.add_argument("--vocos-ckpt", default=DEFAULT_VOCOS_CKPT)
    parser.add_argument("--asr-ckpt",   default=DEFAULT_ASR_CKPT)
    parser.add_argument("--sv-ckpt",    default=DEFAULT_SV_CKPT)
    parser.add_argument("--chunk-size", type=int, default=20)
    parser.add_argument("--steps",      type=int, default=2,
                        help="Flow steps: 1 (fastest), 2 (balanced), 4+ (best quality)")
    parser.add_argument("--seed",       type=int, default=42)
    parser.add_argument(
        "--device", default=None,
        help="Force device: cpu | mps | cuda. Auto-detected if not set.",
    )

    args = parser.parse_args()

    # Seed
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    # Device
    device = get_device(args.device)
    print(f"Device: {device}")

    # Validate checkpoints
    for name, path in [
        ("model-config",  args.model_config),
        ("dit-ckpt",      args.dit_ckpt),
        ("vocos-ckpt",    args.vocos_ckpt),
        ("asr-ckpt",      args.asr_ckpt),
        ("sv-ckpt",       args.sv_ckpt),
        ("reference",     args.reference),
    ]:
        if not os.path.exists(path):
            print(f"ERROR: {name} not found: {path}", file=sys.stderr)
            print("Run:  python download_ckpt.py  to download missing assets.", file=sys.stderr)
            sys.exit(1)

    # Source files
    sources = _collect_sources(args.source)
    if not sources:
        print(f"ERROR: No audio files found at: {args.source}", file=sys.stderr)
        sys.exit(1)
    print(f"Source files  : {len(sources)}")
    print(f"Reference     : {args.reference}")
    print(f"Output dir    : {args.output}")
    print(f"Steps         : {args.steps}")
    print(f"Chunk size    : {args.chunk_size}")

    # Load model config
    with open(args.model_config) as f:
        model_config = json.load(f)

    # DiT
    print("\nLoading DiT…")
    dit_model = DiT(**model_config["model"])
    n_params = sum(p.numel() for p in dit_model.parameters())
    print(f"  Parameters: {n_params:,}")
    dit_model = dit_model.to(device)
    dit_model = load_checkpoint(dit_model, args.dit_ckpt, device=device, use_ema=False)
    dit_model = dit_model.float()
    dit_model.eval()

    # Vocos vocoder (TorchScript)
    print("Loading Vocos vocoder…")
    vocos = torch.jit.load(args.vocos_ckpt, map_location=device)
    vocos.eval()

    # FastU2++ ASR (TorchScript)
    print("Loading FastU2++ ASR…")
    asr_model = torch.jit.load(args.asr_ckpt, map_location=device)
    asr_model.eval()

    # WavLM ECAPA-TDNN speaker verification
    print("Loading WavLM ECAPA-TDNN…")
    sv_model = init_sv_model("wavlm_large", args.sv_ckpt)
    sv_model = sv_model.to(device)
    sv_model.eval()

    # Mel extractor
    mel_extractor = MelSpectrogramFeatures(
        sample_rate=16000, n_fft=1024, win_size=640, hop_length=160,
        n_mels=80, fmin=0.0, fmax=8000.0, center=True,
    ).to(device)

    print("\nAll models loaded ✓")

    convert(
        sources=sources,
        reference_path=args.reference,
        output_dir=args.output,
        dit_model=dit_model,
        vocos=vocos,
        asr_model=asr_model,
        sv_model=sv_model,
        mel_extractor=mel_extractor,
        chunk_size=args.chunk_size,
        steps=args.steps,
        device=device,
    )


if __name__ == "__main__":
    main()
