"""
MeanVC inference engine — singleton wrapper around the full model stack.

Exposes:
  check_assets()      -> dict of asset name -> {path, exists, size_mb}
  get_engine(device)  -> Engine singleton
  Engine.load()
  Engine.convert(source, ref_path, steps, output_dir, progress_cb)
  Engine.calculate_similarity(file_a, file_b)  -> dict
  Engine.check_assets_ok()  -> bool

All model-loading logic mirrors convert.py exactly; no duplication of
inference math.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Callable, Optional

import numpy as np
import torch
import torchaudio

logger = logging.getLogger(__name__)

# Project root — three levels up from meanvc_gui/core/engine.py
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
_ASSETS = os.path.join(_PROJECT_ROOT, "assets")

# ---------------------------------------------------------------------------
# Asset manifest
# ---------------------------------------------------------------------------

REQUIRED_ASSETS: dict[str, dict] = {
    "model_config": {
        "path": os.path.join(_PROJECT_ROOT, "src", "config", "config_200ms.json"),
        "description": "DiT model config (200ms)",
    },
    "dit_ckpt": {
        "path": os.path.join(_ASSETS, "ckpt", "model_200ms.safetensors"),
        "description": "DiT checkpoint (safetensors)",
    },
    "vocos_ckpt": {
        "path": os.path.join(_ASSETS, "ckpt", "vocos.pt"),
        "description": "Vocos vocoder (TorchScript)",
    },
    "asr_ckpt": {
        "path": os.path.join(_ASSETS, "ckpt", "fastu2++.pt"),
        "description": "FastU2++ ASR (TorchScript)",
    },
    "sv_ckpt": {
        "path": os.path.join(_ASSETS, "wavLM", "wavlm_large_finetune.pth"),
        "description": "WavLM ECAPA-TDNN speaker verification",
    },
}


class AssetsMissingError(RuntimeError):
    """Raised when one or more required model assets are missing."""

    def __init__(self, missing: list[str]) -> None:
        paths = "\n  ".join(missing)
        super().__init__(
            f"Missing {len(missing)} required asset(s):\n  {paths}\n"
            "Run: python download_ckpt.py"
        )
        self.missing = missing


def check_assets() -> dict[str, dict]:
    """Return status dict for every required asset.

    Returns:
        {name: {path, exists, size_mb, description}}
    """
    result = {}
    for name, info in REQUIRED_ASSETS.items():
        path = info["path"]
        exists = os.path.isfile(path)
        size_mb = os.path.getsize(path) / 1e6 if exists else 0.0
        result[name] = {
            "path": path,
            "exists": exists,
            "size_mb": round(size_mb, 1),
            "description": info["description"],
        }
    return result


# ---------------------------------------------------------------------------
# Singleton engine
# ---------------------------------------------------------------------------

_ENGINE: Optional["Engine"] = None


def get_engine(device: str = "auto") -> "Engine":
    """Return the application-wide Engine singleton.

    Creates it on first call.  Pass device='auto' to auto-select
    CUDA > MPS > CPU.
    """
    global _ENGINE
    if device == "auto":
        from meanvc_gui.core.device import get_current_device
        device = get_current_device()
    if _ENGINE is None or _ENGINE.device != device:
        _ENGINE = Engine(device)
    return _ENGINE


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class Engine:
    """Full inference engine — loads models once, exposes convert() API."""

    # Hard limits matching convert.py
    SV_MAX_SECS: int = 10
    PROMPT_MAX_FRAMES: int = 500
    C_KV_CACHE_MAX_LEN: int = 100
    DEFAULT_CHUNK_SIZE: int = 20

    def __init__(self, device: str) -> None:
        self.device = device
        self.loaded = False

        # Model handles — set by load()
        self._dit = None
        self._vocos = None
        self._asr = None
        self._sv = None
        self._mel = None
        self._model_config: dict = {}

    # ------------------------------------------------------------------
    # Asset helpers
    # ------------------------------------------------------------------

    def check_assets_ok(self) -> bool:
        return all(v["exists"] for v in check_assets().values())

    def _assert_assets(self) -> None:
        missing = [
            info["path"]
            for info in check_assets().values()
            if not info["exists"]
        ]
        if missing:
            raise AssetsMissingError(missing)

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load all four models.  Raises AssetsMissingError if assets missing."""
        if self.loaded:
            return

        self._assert_assets()

        # Ensure project root on sys.path so src.* imports work
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)

        device = self.device
        t0 = time.time()
        logger.info(f"[Engine] Loading models on device={device} …")

        # Model config
        with open(REQUIRED_ASSETS["model_config"]["path"]) as f:
            self._model_config = json.load(f)

        # DiT
        logger.info("[Engine] Loading DiT …")
        t1 = time.time()
        from src.infer.dit_kvcache import DiT
        from src.model.utils import load_checkpoint
        dit = DiT(**self._model_config["model"])
        dit = dit.to(device)
        dit = load_checkpoint(
            dit,
            REQUIRED_ASSETS["dit_ckpt"]["path"],
            device=device,
            use_ema=False,
        )
        dit = dit.float()
        dit.eval()
        self._dit = dit
        logger.info(f"[Engine] DiT loaded in {time.time()-t1:.1f}s")

        # Vocos
        logger.info("[Engine] Loading Vocos …")
        t1 = time.time()
        self._vocos = torch.jit.load(
            REQUIRED_ASSETS["vocos_ckpt"]["path"], map_location=device
        )
        self._vocos.eval()
        logger.info(f"[Engine] Vocos loaded in {time.time()-t1:.1f}s")

        # FastU2++ ASR
        logger.info("[Engine] Loading FastU2++ ASR …")
        t1 = time.time()
        self._asr = torch.jit.load(
            REQUIRED_ASSETS["asr_ckpt"]["path"], map_location=device
        )
        self._asr.eval()
        logger.info(f"[Engine] ASR loaded in {time.time()-t1:.1f}s")

        # WavLM ECAPA-TDNN
        logger.info("[Engine] Loading WavLM ECAPA-TDNN …")
        t1 = time.time()
        from src.runtime.speaker_verification.verification import init_model as init_sv
        self._sv = init_sv("wavlm_large", REQUIRED_ASSETS["sv_ckpt"]["path"])
        self._sv = self._sv.to(device)
        self._sv.eval()
        logger.info(f"[Engine] WavLM loaded in {time.time()-t1:.1f}s")

        # Mel extractor
        from src.utils.audio import MelSpectrogramFeatures
        self._mel = MelSpectrogramFeatures(
            sample_rate=16000,
            n_fft=1024,
            win_size=640,
            hop_length=160,
            n_mels=80,
            fmin=0.0,
            fmax=8000.0,
            center=True,
        ).to(device)

        self.loaded = True
        logger.info(f"[Engine] All models ready in {time.time()-t0:.1f}s")

    # ------------------------------------------------------------------
    # Feature extraction (mirrors convert.py helpers)
    # ------------------------------------------------------------------

    def _extract_bn(self, source_path: str) -> torch.Tensor:
        """BN features [1, T*4, 256] from source audio."""
        import librosa
        import torchaudio.compliance.kaldi as kaldi

        wav_np, _ = librosa.load(source_path, sr=16000)
        wav_scaled = wav_np * (1 << 15)
        fbanks = kaldi.fbank(
            torch.from_numpy(wav_scaled).unsqueeze(0),
            frame_length=25.0,
            frame_shift=10.0,
            snip_edges=True,
            num_mel_bins=80,
            energy_floor=0.0,
            dither=0.0,
            sample_frequency=16000,
        ).unsqueeze(0).float().to(self.device)

        decoding_chunk_size   = 5
        num_decoding_left     = 2
        subsampling           = 4
        context               = 7
        stride                = subsampling * decoding_chunk_size
        required_cache_size   = decoding_chunk_size * num_decoding_left
        decoding_window       = (decoding_chunk_size - 1) * subsampling + context

        att_cache = torch.zeros((0, 0, 0, 0), device=self.device)
        cnn_cache = torch.zeros((0, 0, 0, 0), device=self.device)
        bn_chunks: list[torch.Tensor] = []
        offset = 0

        with torch.no_grad():
            for i in range(0, fbanks.shape[1], stride):
                chunk = fbanks[:, i: i + decoding_window, :]
                if chunk.shape[1] < required_cache_size:
                    pad = required_cache_size - chunk.shape[1]
                    chunk = torch.nn.functional.pad(
                        chunk, (0, 0, 0, pad), mode="constant", value=0.0
                    )
                enc_out, att_cache, cnn_cache = self._asr.forward_encoder_chunk(
                    chunk, offset, required_cache_size, att_cache, cnn_cache
                )
                offset += enc_out.size(1)
                bn_chunks.append(enc_out)

        bn = torch.cat(bn_chunks, dim=1).transpose(1, 2)
        bn = torch.nn.functional.interpolate(
            bn, size=int(bn.shape[2] * 4), mode="linear", align_corners=True
        ).transpose(1, 2)
        return bn

    def _extract_spk_and_prompt(
        self, ref_path: str
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """(spk_emb [1,192], prompt_mel [1,T,80]) from reference audio."""
        wav, sr = torchaudio.load(ref_path)
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        if sr != 16000:
            wav = torchaudio.transforms.Resample(sr, 16000)(wav)

        max_sv = self.SV_MAX_SECS * 16000
        sv_wav = wav[:, :max_sv] if wav.shape[1] > max_sv else wav
        max_prompt = self.PROMPT_MAX_FRAMES * 160
        prompt_wav = wav[:, :max_prompt] if wav.shape[1] > max_prompt else wav

        sv_wav    = sv_wav.to(self.device)
        prompt_wav = prompt_wav.to(self.device)

        with torch.no_grad():
            spk_emb    = self._sv(sv_wav)
            prompt_mel = self._mel(prompt_wav).transpose(1, 2)

        return spk_emb, prompt_mel

    @torch.inference_mode()
    def _run_inference(
        self,
        bn: torch.Tensor,
        spk_emb: torch.Tensor,
        prompt_mel: torch.Tensor,
        steps: int,
        chunk_size: int,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Flow-matching inference → (mel [1,80,T], wav [1,T_wav])."""
        if steps == 1:
            timesteps = torch.tensor([1.0, 0.0], device=self.device)
        elif steps == 2:
            timesteps = torch.tensor([1.0, 0.8, 0.0], device=self.device)
        else:
            timesteps = torch.linspace(1.0, 0.0, steps + 1, device=self.device)

        seq_len = bn.shape[1]
        cache: torch.Tensor | None = None
        x_parts: list[torch.Tensor] = []
        offset = 0
        kv_cache = None
        B = 1

        for start in range(0, seq_len, chunk_size):
            end = min(start + chunk_size, seq_len)
            bn_chunk = bn[:, start:end]

            x = torch.randn(
                B, bn_chunk.shape[1], 80,
                device=self.device, dtype=bn_chunk.dtype
            )

            for i in range(steps):
                t = timesteps[i]
                r = timesteps[i + 1]
                t_t = torch.full((B,), t, device=self.device)
                r_t = torch.full((B,), r, device=self.device)
                u, tmp_kv = self._dit(
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

            # Trim KV cache to avoid quadratic growth
            if (
                offset > 40
                and kv_cache is not None
                and kv_cache[0][0].shape[2] > self.C_KV_CACHE_MAX_LEN
            ):
                for i in range(len(kv_cache)):
                    kv_cache[i] = (
                        kv_cache[i][0][:, :, -self.C_KV_CACHE_MAX_LEN:, :],
                        kv_cache[i][1][:, :, -self.C_KV_CACHE_MAX_LEN:, :],
                    )

        mel = torch.cat(x_parts, dim=1).transpose(1, 2)
        mel = (mel + 1) / 2
        wav = self._vocos.decode(mel)
        return mel, wav

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(
        self,
        source_path: str,
        ref_path: str,
        steps: int = 2,
        output_dir: str | None = None,
        progress_cb: Callable[[int, str], None] | None = None,
        cancelled_cb: Callable[[], bool] | None = None,
    ) -> str:
        """Convert source audio to target speaker.

        Args:
            source_path:  Path to source audio file.
            ref_path:     Path to reference (target speaker) audio.
            steps:        Denoising steps (1=fastest, 2=balanced, 4=best).
            output_dir:   Directory for output wav.  Defaults to
                          <project_root>/meanvc_out/.
            progress_cb:  Optional callback(percent: int, message: str).
            cancelled_cb: Optional callback() -> bool; if returns True,
                          conversion aborts and raises RuntimeError.

        Returns:
            Path to the output wav file.
        """
        if not self.loaded:
            self.load()

        def _progress(pct: int, msg: str) -> None:
            logger.info(f"[Engine.convert] {pct}% — {msg}")
            if progress_cb:
                progress_cb(pct, msg)

        def _check_cancel() -> None:
            if cancelled_cb and cancelled_cb():
                raise RuntimeError("Conversion cancelled by user")

        if output_dir is None:
            output_dir = os.path.join(_PROJECT_ROOT, "meanvc_out")
        os.makedirs(output_dir, exist_ok=True)

        stem = os.path.splitext(os.path.basename(source_path))[0]
        out_path = os.path.join(output_dir, f"{stem}_converted.wav")

        try:
            _progress(0, "Extracting content features …")
            bn = self._extract_bn(source_path)
            _check_cancel()

            _progress(33, "Extracting speaker embedding …")
            spk_emb, prompt_mel = self._extract_spk_and_prompt(ref_path)
            _check_cancel()

            _progress(66, "Running flow-matching inference …")
            t0 = time.time()
            mel, wav = self._run_inference(
                bn, spk_emb, prompt_mel,
                steps=steps, chunk_size=self.DEFAULT_CHUNK_SIZE,
            )
            duration = wav.shape[1] / 16000
            elapsed  = time.time() - t0
            rtf      = elapsed / max(duration, 1e-6)
            logger.info(f"[Engine.convert] RTF={rtf:.4f} ({duration:.2f}s audio, {elapsed:.2f}s inference)")
            _check_cancel()

            _progress(90, "Saving output …")
            torchaudio.save(out_path, wav.cpu(), 16000)
            _progress(100, "Done")

        except RuntimeError as exc:
            if "cancelled" in str(exc).lower():
                raise
            raise RuntimeError(f"Conversion failed: {exc}") from exc

        return out_path

    def calculate_similarity(self, file_a: str, file_b: str) -> dict:
        """Compute ECAPA-TDNN cosine speaker similarity between two files.

        Returns:
            dict with keys: similarity (0-100), duration_a, duration_b,
                            quality_a, quality_b.
        """
        if not self.loaded:
            self.load()

        import torch.nn.functional as F

        def _embed(path: str) -> tuple[torch.Tensor, float, float]:
            wav, sr = torchaudio.load(path)
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0, keepdim=True)
            if sr != 16000:
                wav = torchaudio.transforms.Resample(sr, 16000)(wav)
            duration = wav.shape[1] / 16000
            # RMS for quality proxy (in dBFS)
            rms_db = 20 * np.log10(
                float(wav.abs().mean()) + 1e-9
            )
            max_samples = self.SV_MAX_SECS * 16000
            wav = wav[:, :max_samples].to(self.device)
            with torch.no_grad():
                emb = self._sv(wav)  # [1, 192]
            return emb, duration, rms_db

        t0 = time.time()
        emb_a, dur_a, rms_a = _embed(file_a)
        emb_b, dur_b, rms_b = _embed(file_b)

        cos_sim = F.cosine_similarity(emb_a, emb_b).item()
        similarity = round(float((cos_sim + 1) / 2 * 100), 1)  # map [-1,1] → [0,100]

        def _quality(rms_db: float) -> str:
            if rms_db > -25:
                return "Good"
            if rms_db > -40:
                return "Fair"
            return "Low"

        logger.info(
            f"[Engine.similarity] {similarity:.1f}%  "
            f"(elapsed {time.time()-t0:.2f}s)"
        )
        return {
            "similarity": similarity,
            "duration_a": round(dur_a, 2),
            "duration_b": round(dur_b, 2),
            "quality_a": _quality(rms_a),
            "quality_b": _quality(rms_b),
            "emb_a": emb_a.squeeze().cpu().tolist(),
            "emb_b": emb_b.squeeze().cpu().tolist(),
        }

    def get_sv_model(self):
        """Return the loaded speaker verification model (for VCRunner)."""
        if not self.loaded:
            self.load()
        return self._sv

    def get_models(self) -> dict:
        """Return all loaded models (for VCRunner realtime pipeline)."""
        if not self.loaded:
            self.load()
        return {
            "dit":    self._dit,
            "vocos":  self._vocos,
            "asr":    self._asr,
            "sv":     self._sv,
            "mel":    self._mel,
            "device": self.device,
            "config": self._model_config,
        }
