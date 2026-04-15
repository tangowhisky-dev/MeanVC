"""Real-time voice conversion runner.

Streams microphone input through the MeanVC pipeline and plays the
converted audio in real-time using PyAudio.

Changes vs original:
  * All checkpoint paths resolve to assets/ folder (no more src/ckpt/)
  * MelSpectrogramFeatures uses return_complex=True (PyTorch ≥ 2.0)
  * load_wav / torchaudio.load used for reference speaker audio (no soundfile)
  * No torchaudio backend monkey-patching
"""

from __future__ import annotations

import os
import time
import argparse
import json
import numpy as np
import torch
import torch.nn as nn
from threading import Thread, Lock
from tqdm import tqdm
import torchaudio
import torchaudio.compliance.kaldi as kaldi
import librosa

from src.runtime.speaker_verification.verification import init_model as init_sv_model
from src.utils.audio import MelSpectrogramFeatures, get_device

# ---------------------------------------------------------------------------
# Project root — checkpoint paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_ASSETS = os.path.join(_PROJECT_ROOT, "assets")


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


# ---------------------------------------------------------------------------
# VCRunner
# ---------------------------------------------------------------------------

class VCRunner:
    """Real-time voice conversion engine."""

    def __init__(self, target_path: str, steps: int = 2) -> None:
        self.mutex = Lock()
        torch.set_num_threads(1)

        # Speaker verification model
        sv_ckpt = os.path.join(_ASSETS, "wavLM", "wavlm_large_finetune.pth")
        self.sv_model = init_sv_model("wavlm_large", sv_ckpt)
        self.sv_model.eval()

        self.steps = steps
        if self.steps == 1:
            self.timesteps = torch.tensor([1.0, 0.0])
        elif self.steps == 2:
            self.timesteps = torch.tensor([1.0, 0.8, 0.0])
        else:
            self.timesteps = torch.linspace(1.0, 0.0, self.steps + 1)

        # Mel extractor (MPS/CPU compatible, return_complex=True)
        self.mel_extract = MelSpectrogramFeatures(
            sample_rate=16000, n_fft=1024, win_size=640, hop_length=160,
            n_mels=80, fmin=0, fmax=8000, center=True
        )

        # TorchScript models from assets/
        asr_ckpt = os.path.join(_ASSETS, "ckpt", "fastu2++.pt")
        vc_ckpt = os.path.join(_ASSETS, "ckpt", "meanvc_200ms.pt")
        vocos_ckpt = os.path.join(_ASSETS, "ckpt", "vocos.pt")

        self.asr = torch.jit.load(asr_ckpt)
        self.vc = torch.jit.load(vc_ckpt)
        self.vocoder = torch.jit.load(vocos_ckpt)

        # Streaming parameters
        decoding_chunk_size = 5
        num_decoding_left_chunks = 2
        subsampling = 4
        context = 7
        stride = subsampling * decoding_chunk_size
        decoding_window = (decoding_chunk_size - 1) * subsampling + context
        self.required_cache_size = decoding_chunk_size * num_decoding_left_chunks
        self.CHUNK = 160 * stride
        self.vc_chunk = int(decoding_chunk_size * 4)
        self.vocoder_overlap = 3
        upsample_factor = 160
        self.vocoder_wav_overlap = (self.vocoder_overlap - 1) * upsample_factor
        self.down_linspace = torch.linspace(1, 0, steps=self.vocoder_wav_overlap).numpy()
        self.up_linspace = torch.linspace(0, 1, steps=self.vocoder_wav_overlap).numpy()

        # Load reference speaker audio using torchaudio (TorchCodec backend)
        wav, sr = torchaudio.load(target_path)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        if sr != 16000:
            wav = torchaudio.transforms.Resample(sr, 16000)(wav)

        with torch.no_grad():
            spk_emb = self.sv_model(wav)
        self.vc_spk_emb = spk_emb

        prompt_mel = self.mel_extract(wav)
        self.vc_prompt_mel = prompt_mel.transpose(1, 2)  # [1, T, 80]

    # ------------------------------------------------------------------
    def playaudio(self, out_stream, data: bytes) -> None:
        with self.mutex:
            out_stream.write(data)

    def init_cache(self) -> None:
        self.samples_cache_len = 720
        self.samples_cache: np.ndarray | None = None

        self.att_cache = torch.zeros((0, 0, 0, 0), device="cpu")
        self.cnn_cache = torch.zeros((0, 0, 0, 0), device="cpu")
        self.asr_offset = 0
        self.encoder_output_cache: torch.Tensor | None = None

        self.vc_offset = 0
        self.vc_cache: torch.Tensor | None = None
        self.vc_kv_cache = None

        self.vocoder_cache: torch.Tensor | None = None
        self.last_wav: np.ndarray | None = None
        self.need_extra_data = True

    def reset_cache(self) -> None:
        self.asr_offset = 20
        self.vc_offset = 120

    def cleanup(self) -> None:
        """Release audio streams if open."""
        if hasattr(self, "in_stream"):
            try:
                self.in_stream.stop_stream()
                self.in_stream.close()
            except Exception:
                pass
        if hasattr(self, "out_stream"):
            try:
                self.out_stream.stop_stream()
                self.out_stream.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    def inference_one_chunk(self, samples: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            if self.samples_cache is None:
                pass
            else:
                samples = np.concatenate((self.samples_cache, samples))
            self.samples_cache = samples[-self.samples_cache_len :]

            fbanks = extract_fbanks(samples, frame_shift=10).float()
            encoder_output, self.att_cache, self.cnn_cache = self.asr.forward_encoder_chunk(
                fbanks, self.asr_offset, self.required_cache_size,
                self.att_cache, self.cnn_cache,
            )

            self.asr_offset += encoder_output.size(1)
            if self.encoder_output_cache is None:
                encoder_output = torch.cat(
                    [encoder_output[:, 0:1, :], encoder_output], dim=1
                )
            else:
                encoder_output = torch.cat(
                    [self.encoder_output_cache, encoder_output], dim=1
                )
            self.encoder_output_cache = encoder_output[:, -1:, :]

            enc_up = encoder_output.transpose(1, 2)
            enc_up = torch.nn.functional.interpolate(
                enc_up, size=self.vc_chunk + 1, mode="linear", align_corners=True
            )
            enc_up = enc_up.transpose(1, 2)[:, 1:, :]

            x = torch.randn(1, enc_up.shape[1], 80, dtype=enc_up.dtype)

            for i in range(self.steps):
                t = self.timesteps[i]
                r = self.timesteps[i + 1]
                t_t = torch.full((1,), t)
                r_t = torch.full((1,), r)
                u, tmp_kv_cache = self.vc(
                    x, t_t, r_t,
                    cache=self.vc_cache, cond=enc_up, spks=self.vc_spk_emb,
                    prompts=self.vc_prompt_mel, offset=self.vc_offset,
                    kv_cache=self.vc_kv_cache,
                )
                x = x - (t - r) * u

            self.vc_kv_cache = tmp_kv_cache
            self.vc_offset += x.shape[1]
            self.vc_cache = x

            VC_KV_CACHE_MAX_LEN = 100
            if (
                self.vc_offset > 40
                and self.vc_kv_cache is not None
                and self.vc_kv_cache[0][0].shape[2] > VC_KV_CACHE_MAX_LEN
            ):
                for i in range(len(self.vc_kv_cache)):
                    nk = self.vc_kv_cache[i][0][:, :, -VC_KV_CACHE_MAX_LEN:, :]
                    nv = self.vc_kv_cache[i][1][:, :, -VC_KV_CACHE_MAX_LEN:, :]
                    self.vc_kv_cache[i] = (nk, nv)

            mel = x.transpose(1, 2)
            if self.vocoder_cache is not None:
                mel = torch.cat([self.vocoder_cache, mel], dim=-1)
            self.vocoder_cache = mel[:, :, -self.vocoder_overlap :]
            mel = (mel + 1) / 2
            wav_out = self.vocoder.decode(mel).squeeze()
            wav_np = wav_out.detach().cpu().numpy()

            if self.last_wav is not None:
                front = wav_np[: self.vocoder_wav_overlap]
                smooth = (
                    self.last_wav * self.down_linspace
                    + front * self.up_linspace
                )
                new_wav = np.concatenate(
                    [smooth, wav_np[self.vocoder_wav_overlap : -self.vocoder_wav_overlap]]
                )
            else:
                new_wav = wav_np[: -self.vocoder_wav_overlap]
            self.last_wav = wav_np[-self.vocoder_wav_overlap :]

            return new_wav

    # ------------------------------------------------------------------
    def run(self) -> None:
        import pyaudio

        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get("deviceCount")

        print("=== Input Device List ===")
        input_devices: list[int] = []
        for i in range(numdevices):
            dev = p.get_device_info_by_host_api_device_index(0, i)
            if dev.get("maxInputChannels") > 0:
                print(f"  Input Device id {i} - {dev.get('name')}")
                input_devices.append(i)

        print("\n=== Output Device List ===")
        output_devices: list[int] = []
        for i in range(numdevices):
            dev = p.get_device_info_by_host_api_device_index(0, i)
            if dev.get("maxOutputChannels") > 0:
                print(f"  Output Device id {i} - {dev.get('name')}")
                output_devices.append(i)

        input_device_id = int(input("Select input device ID: "))
        output_device_id = int(input("Select output device ID: "))

        if input_device_id not in input_devices:
            input_device_id = p.get_default_input_device_info()["index"]
        if output_device_id not in output_devices:
            output_device_id = p.get_default_output_device_info()["index"]

        print("Warming up…")

        self.in_stream = p.open(
            format=pyaudio.paInt16, channels=1, rate=16000,
            input=True, input_device_index=input_device_id,
            frames_per_buffer=self.CHUNK,
        )
        self.out_stream = p.open(
            format=pyaudio.paFloat32, channels=1, rate=16000,
            output=True, output_device_index=output_device_id,
        )

        for _ in tqdm(range(10), desc="warmup"):
            data = self.in_stream.read(self.CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / (1 << 15)
            Thread(target=self.playaudio, args=(self.out_stream, samples.tobytes())).start()

        self.init_cache()

        i = 0
        while True:
            if i % 50 == 0 and i != 0:
                print("reset!")
                self.reset_cache()

            data = self.in_stream.read(self.CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / (1 << 15)

            if self.need_extra_data:
                extra = self.in_stream.read(720, exception_on_overflow=False)
                extra_s = np.frombuffer(extra, dtype=np.int16).astype(np.float32) / (1 << 15)
                samples = np.concatenate([samples, extra_s])
                self.need_extra_data = False

            t0 = time.time()
            vc_wav = self.inference_one_chunk(samples)
            processed_duration = len(samples) / 16000
            Thread(target=self.playaudio, args=(self.out_stream, vc_wav.tobytes())).start()
            print(f"chunk time {time.time() - t0:.3f}s  chunk size {processed_duration:.3f}s")
            i += 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="MeanVC real-time voice conversion")
    parser.add_argument(
        "--target-path",
        default=os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "example", "test.wav"
        ),
        help="Reference speaker audio file (target voice)",
    )
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    torch.set_num_threads(1)
    torch.manual_seed(args.seed)

    runner = VCRunner(args.target_path, steps=args.steps)
    try:
        runner.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        runner.cleanup()


if __name__ == "__main__":
    main()
