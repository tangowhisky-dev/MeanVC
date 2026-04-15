"""
Shared audio utilities for MeanVC.

Provides:
  - MelSpectrogramFeatures: custom mel extractor used throughout inference
  - get_device(): auto-selects the best available device (CUDA > MPS > CPU)
  - load_wav(): load any audio file, resample to target SR, mono-mix

All torch.stft calls use return_complex=True (PyTorch ≥ 2.0 API).
"""

from __future__ import annotations

import os
import torch
import torch.nn as nn
import torchaudio
import numpy as np
import librosa
from librosa.filters import mel as librosa_mel_fn


# ---------------------------------------------------------------------------
# Device helper
# ---------------------------------------------------------------------------


def get_device(prefer: str | None = None) -> str:
    """Return the best available torch device string.

    Priority: MEANVC_DEVICE env var → prefer (if given & available) → cuda → mps → cpu.

    The environment variable MEANVC_DEVICE can be set to: cpu, mps, cuda, cuda:0, etc.

    Args:
        prefer: Optional explicit device string (``'cpu'``, ``'mps'``,
                ``'cuda'``, ``'cuda:0'``, …).  If unavailable, falls
                back to auto-selection.
    """
    env_device = os.environ.get("MEANVC_DEVICE", None)
    if env_device is not None:
        if env_device.startswith("cuda") and torch.cuda.is_available():
            return env_device
        if env_device == "mps" and torch.backends.mps.is_available():
            return "mps"
        if env_device == "cpu":
            return "cpu"

    if prefer is not None:
        if prefer.startswith("cuda") and torch.cuda.is_available():
            return prefer
        if prefer == "mps" and torch.backends.mps.is_available():
            return "mps"
        if prefer == "cpu":
            return "cpu"

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ---------------------------------------------------------------------------
# Mel spectrogram (custom — matches MeanVC training recipe)
# ---------------------------------------------------------------------------


def _amp_to_db(x: torch.Tensor, min_level_db: float) -> torch.Tensor:
    min_level = np.exp(min_level_db / 20 * np.log(10))
    min_level_t = torch.ones_like(x) * min_level
    return 20 * torch.log10(torch.maximum(min_level_t, x))


def _normalize(S: torch.Tensor, max_abs_value: float, min_db: float) -> torch.Tensor:
    return torch.clamp(
        (2 * max_abs_value) * ((S - min_db) / (-min_db)) - max_abs_value,
        -max_abs_value,
        max_abs_value,
    )


class MelSpectrogramFeatures(nn.Module):
    """Custom mel-spectrogram extractor matching the MeanVC training recipe.

    Uses ``torch.stft`` with ``return_complex=True`` (PyTorch ≥ 2.0).
    The old ``return_complex=False`` path has been removed — it was
    deprecated in PyTorch 2.x and will be removed in a future release.

    Parameters
    ----------
    sample_rate : int
    n_fft : int
    win_size : int
    hop_length : int
    n_mels : int
    fmin : float
    fmax : float
    center : bool
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        n_fft: int = 1024,
        win_size: int = 640,
        hop_length: int = 160,
        n_mels: int = 80,
        fmin: float = 0.0,
        fmax: float = 8000.0,
        center: bool = True,
    ):
        super().__init__()

        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.win_size = win_size
        self.fmin = fmin
        self.fmax = fmax
        self.center = center

        # Lazily populated per dtype/device combination to avoid re-allocation
        self.mel_basis: dict[str, torch.Tensor] = {}
        self.hann_window: dict[str, torch.Tensor] = {}

    def forward(self, y: torch.Tensor) -> torch.Tensor:
        """Compute mel-spectrogram from waveform.

        Args:
            y: Waveform tensor of shape ``(B, T)`` or ``(T,)``.

        Returns:
            Mel spectrogram of shape ``(B, n_mels, frames)`` or
            ``(n_mels, frames)`` (matching input rank).
        """
        dtype_device = f"{y.dtype}_{y.device}"
        fmax_key = f"{self.fmax}_{dtype_device}"
        win_key = f"{self.win_size}_{dtype_device}"

        if fmax_key not in self.mel_basis:
            mel_np = librosa_mel_fn(
                sr=self.sample_rate,
                n_fft=self.n_fft,
                n_mels=self.n_mels,
                fmin=self.fmin,
                fmax=self.fmax,
            )
            self.mel_basis[fmax_key] = torch.from_numpy(mel_np).to(
                dtype=y.dtype, device=y.device
            )

        if win_key not in self.hann_window:
            self.hann_window[win_key] = torch.hann_window(self.win_size).to(
                dtype=y.dtype, device=y.device
            )

        # --- STFT with return_complex=True (PyTorch ≥ 2.0 clean API) -------
        spec_complex = torch.stft(
            y,
            self.n_fft,
            hop_length=self.hop_length,
            win_length=self.win_size,
            window=self.hann_window[win_key],
            center=self.center,
            pad_mode="reflect",
            normalized=False,
            onesided=True,
            return_complex=True,  # ← modern API; no deprecation warning
        )
        # Magnitude: |complex| = sqrt(re² + im²)
        spec = spec_complex.abs()
        # Numerical stability guard
        spec = torch.sqrt(spec.pow(2) + 1e-6)

        # Apply mel filterbank
        spec = torch.matmul(self.mel_basis[fmax_key], spec)

        # Convert to dB scale and normalise
        spec = _amp_to_db(spec, -115) - 20
        spec = _normalize(spec, 1, -115)

        return spec


# ---------------------------------------------------------------------------
# Audio loading helper
# ---------------------------------------------------------------------------


def load_wav(
    path: str,
    target_sr: int = 16000,
    mono: bool = True,
) -> tuple[torch.Tensor, int]:
    """Load an audio file and resample to ``target_sr``.

    Uses ``torchaudio.load`` (TorchCodec backend, torchaudio ≥ 2.9).

    Args:
        path: Path to an audio file (wav, mp3, flac, …).
        target_sr: Desired sample rate.
        mono: If True, average stereo channels to mono.

    Returns:
        ``(waveform, sample_rate)`` where waveform is ``(1, T)`` float32.
    """
    wav, sr = torchaudio.load(path)  # shape: (C, T), float32

    if mono and wav.shape[0] > 1:
        wav = wav.mean(dim=0, keepdim=True)  # (1, T)

    if sr != target_sr:
        resampler = torchaudio.transforms.Resample(orig_freq=sr, new_freq=target_sr)
        wav = resampler(wav)

    return wav, target_sr
