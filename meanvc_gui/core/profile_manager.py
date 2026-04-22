"""MeanVC Profile Manager.

Handles voice profile creation, audio processing, and embedding extraction.
"""

import os
import logging
import shutil
import zipfile
import json
import numpy as np
import torch
import torchaudio
from typing import Optional
import uuid

from meanvc_gui.core.profile_db import ProfileDB

logger = logging.getLogger(__name__)


def get_project_root():
    """Get project root directory (three levels up from meanvc_gui/core/)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_PROJECT_ROOT = get_project_root()
_SV_CKPT_PATH = os.path.join(_PROJECT_ROOT, "assets", "wavLM", "wavlm_large_finetune.pth")
_SV_MAX_SECS = 10  # must match Engine.SV_MAX_SECS


def get_audio_duration(file_path: str) -> float:
    """Get audio file duration in seconds."""
    # torchaudio.info is unavailable in some builds — use soundfile as primary,
    # fall back to loading the full waveform if needed.
    try:
        import soundfile as sf
        return sf.info(file_path).duration
    except Exception:
        pass
    try:
        wav, sr = torchaudio.load(file_path)
        return wav.shape[1] / sr
    except Exception:
        return 0.0


def extract_wavlm_embedding(
    audio_path: str, output_path: str, device: str = "cpu"
) -> bool:
    """Extract WavLM ECAPA-TDNN speaker embedding from audio file.

    Uses the same init_sv_model path as engine.py and convert.py.
    Saves a [1, 256] tensor to output_path.

    Args:
        audio_path:  Path to input audio (wav/mp3/flac).
        output_path: Path to save embedding (.pt file).
        device:      Torch device string.

    Returns:
        bool: True on success.
    """
    if not os.path.isfile(_SV_CKPT_PATH):
        logger.warning(
            f"WavLM checkpoint not found at {_SV_CKPT_PATH}. "
            "Embedding extraction skipped. Run download_ckpt.py first."
        )
        return False

    try:
        import sys
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from src.runtime.speaker_verification.verification import (
            init_model as init_sv,
        )

        t0 = __import__("time").time()
        sv_model = init_sv("wavlm_large", _SV_CKPT_PATH)
        sv_model = sv_model.to(device)
        sv_model.eval()

        waveform, sr = torchaudio.load(audio_path)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sr != 16000:
            waveform = torchaudio.transforms.Resample(sr, 16000)(waveform)

        # Cap at SV_MAX_SECS to avoid WavLM OOM
        max_samples = _SV_MAX_SECS * 16000
        if waveform.shape[1] > max_samples:
            waveform = waveform[:, :max_samples]

        waveform = waveform.to(device)
        with torch.no_grad():
            embedding = sv_model(waveform)  # [1, 256]

        torch.save(embedding.cpu(), output_path)
        elapsed = __import__("time").time() - t0
        logger.info(
            f"[profile_manager] Embedding extracted: shape={list(embedding.shape)} "
            f"in {elapsed:.2f}s → {output_path}"
        )
        return True

    except Exception as exc:
        logger.error(f"[profile_manager] extract_wavlm_embedding failed: {exc}", exc_info=True)
        return False


def extract_mel_spectrogram(audio_path: str, output_path: str) -> bool:
    """Extract mel spectrogram using MelSpectrogramFeatures (project-native).

    Uses the same filterbank as the inference pipeline. Do NOT use
    torchaudio.transforms.MelSpectrogram — different filterbank values.

    Args:
        audio_path:  Path to input audio.
        output_path: Path to save mel (.npy file, shape [80, T]).

    Returns:
        bool: True on success.
    """
    try:
        import sys
        if _PROJECT_ROOT not in sys.path:
            sys.path.insert(0, _PROJECT_ROOT)
        from src.utils.audio import MelSpectrogramFeatures

        waveform, sr = torchaudio.load(audio_path)
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        if sr != 16000:
            waveform = torchaudio.transforms.Resample(sr, 16000)(waveform)

        mel_fn = MelSpectrogramFeatures(
            sample_rate=16000,
            n_fft=1024,
            win_size=640,
            hop_length=160,
            n_mels=80,
            fmin=0.0,
            fmax=8000.0,
            center=True,
        )
        with torch.no_grad():
            mel = mel_fn(waveform)  # [1, 80, T]

        np.save(output_path, mel.squeeze(0).numpy())  # [80, T]
        return True

    except Exception as exc:
        logger.error(f"[profile_manager] extract_mel_spectrogram failed: {exc}", exc_info=True)
        return False


def copy_audio_file(source_path: str, dest_path: str) -> bool:
    """Copy audio file to profile directory.

    Args:
        source_path: Source file path
        dest_path: Destination file path

    Returns:
        bool: Success
    """
    try:
        import shutil

        shutil.copy2(source_path, dest_path)
        return True
    except Exception as e:
        print(f"Error copying audio file: {e}")
        return False


class ProfileManager:
    """Manager for voice profiles."""

    def __init__(self):
        """Initialize profile manager."""
        self.db = ProfileDB()

    def create_profile(self, name: str, description: str = "") -> dict:
        """Create new voice profile.

        Args:
            name: Profile name
            description: Optional description

        Returns:
            dict: Created profile
        """
        return self.db.create_profile(name, description)

    def get_profile(self, profile_id: str) -> Optional[dict]:
        """Get profile by ID.

        Args:
            profile_id: Profile ID

        Returns:
            dict: Profile data
        """
        return self.db.get_profile(profile_id)

    def list_profiles(self) -> list[dict]:
        """List all profiles.

        Returns:
            list: All profiles
        """
        return self.db.list_profiles()

    def update_profile(
        self, profile_id: str, name: str = None, description: str = None
    ) -> dict:
        """Update profile.

        Args:
            profile_id: Profile ID
            name: New name
            description: New description

        Returns:
            dict: Updated profile
        """
        return self.db.update_profile(profile_id, name, description)

    def delete_profile(self, profile_id: str) -> bool:
        """Delete profile.

        Args:
            profile_id: Profile ID

        Returns:
            bool: Success
        """
        return self.db.delete_profile(profile_id)

    def add_audio(
        self,
        profile_id: str,
        source_path: str,
        filename: str = None,
        extract_embedding: bool = True,
        extract_mel: bool = True,
        is_default: bool = False,
        device: str = "cpu",
    ) -> dict:
        """Add audio file to profile.

        Args:
            profile_id: Profile ID
            source_path: Source audio file path
            filename: Optional filename (default: use source filename)
            extract_embedding: Extract speaker embedding
            extract_mel: Extract mel spectrogram
            is_default: Set as default reference
            device: Device for embedding extraction

        Returns:
            dict: Added audio file
        """
        profile = self.db.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"Profile not found: {profile_id}")

        # Determine filename
        if filename is None:
            filename = os.path.basename(source_path)

        # Generate unique ID for files
        file_id = uuid.uuid4().hex

        # Get profile directories
        profile_dir = self.db.get_profile_dir(profile_id)
        audio_dir = os.path.join(profile_dir, "audio")
        embedding_dir = os.path.join(profile_dir, "embeddings")
        prompt_dir = os.path.join(profile_dir, "prompt")

        # Copy audio file
        dest_filename = f"{file_id}_{filename}"
        dest_audio_path = os.path.join(audio_dir, dest_filename)

        if not copy_audio_file(source_path, dest_audio_path):
            raise RuntimeError("Failed to copy audio file")

        # Get duration
        duration = get_audio_duration(dest_audio_path)

        # Paths for embedding and mel
        embedding_path = None
        mel_path = None

        # Extract embedding
        if extract_embedding:
            embedding_path = os.path.join(embedding_dir, f"{file_id}.pt")
            extract_wavlm_embedding(dest_audio_path, embedding_path, device)

        # Extract mel spectrogram
        if extract_mel:
            mel_path = os.path.join(prompt_dir, f"{file_id}_mel.npy")
            extract_mel_spectrogram(dest_audio_path, mel_path)

        # Add to database
        return self.db.add_audio_file(
            profile_id=profile_id,
            filename=filename,
            file_path=dest_audio_path,
            duration=duration,
            embedding_path=embedding_path,
            mel_path=mel_path,
            is_default=is_default,
        )

    def delete_audio(self, file_id: str) -> bool:
        """Delete audio file from profile.

        Args:
            file_id: Audio file ID

        Returns:
            bool: Success
        """
        return self.db.delete_audio_file(file_id)

    def set_default_audio(self, file_id: str) -> bool:
        """Set audio file as default reference.

        Args:
            file_id: Audio file ID

        Returns:
            bool: Success
        """
        return self.db.set_default_audio(file_id)

    def get_default_reference(self, profile_id: str) -> Optional[dict]:
        """Get default reference audio for profile.

        Args:
            profile_id: Profile ID

        Returns:
            dict: Default audio file or None
        """
        audio_files = self.db.get_audio_files(profile_id)
        for af in audio_files:
            if af["is_default"]:
                return af
        # Return first if no default
        return audio_files[0] if audio_files else None

    def load_embedding(self, profile_id: str) -> Optional[torch.Tensor]:
        """Load speaker embedding for profile.

        Args:
            profile_id: Profile ID

        Returns:
            torch.Tensor: Speaker embedding or None
        """
        ref = self.get_default_reference(profile_id)
        if ref and ref.get("embedding_path") and os.path.exists(ref["embedding_path"]):
            return torch.load(ref["embedding_path"])
        return None

    def load_prompt_mel(self, profile_id: str) -> Optional[np.ndarray]:
        """Load prompt mel spectrogram for profile.

        Args:
            profile_id: Profile ID

        Returns:
            np.ndarray: Mel spectrogram or None
        """
        ref = self.get_default_reference(profile_id)
        if ref and ref.get("mel_path") and os.path.exists(ref["mel_path"]):
            return np.load(ref["mel_path"])
        return None


    def export_profile(self, profile_id: str, output_zip_path: str) -> None:
        """Export profile to a zip archive.

        Archive layout:
          manifest.json
          audio/<file_id>_<filename>
          embeddings/<file_id>.pt
          prompt/<file_id>_mel.npy

        Args:
            profile_id:      Profile to export.
            output_zip_path: Destination zip path.
        """
        profile = self.db.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"Profile not found: {profile_id}")

        audio_files = self.db.get_audio_files(profile_id)
        manifest = {
            "version": 1,
            "profile": {
                "name": profile["name"],
                "description": profile.get("description", ""),
            },
            "audio_files": [
                {
                    "filename":       af["filename"],
                    "duration":       af.get("duration", 0),
                    "is_default":     bool(af.get("is_default")),
                    "audio_file":     os.path.basename(af["file_path"]) if af.get("file_path") else None,
                    "embedding_file": os.path.basename(af["embedding_path"]) if af.get("embedding_path") else None,
                    "mel_file":       os.path.basename(af["mel_path"]) if af.get("mel_path") else None,
                }
                for af in audio_files
            ],
        }

        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            for af in audio_files:
                if af.get("file_path") and os.path.isfile(af["file_path"]):
                    zf.write(af["file_path"], f"audio/{os.path.basename(af['file_path'])}")
                if af.get("embedding_path") and os.path.isfile(af["embedding_path"]):
                    zf.write(af["embedding_path"], f"embeddings/{os.path.basename(af['embedding_path'])}")
                if af.get("mel_path") and os.path.isfile(af["mel_path"]):
                    zf.write(af["mel_path"], f"prompt/{os.path.basename(af['mel_path'])}")

        logger.info(f"[profile_manager] Exported {profile['name']} → {output_zip_path}")

    def import_profile(self, zip_path: str) -> dict:
        """Import a profile from a zip archive.

        Creates a new profile with a fresh UUID, copies all audio and
        embedding files to the new profile directory, and registers them
        in the database.

        Args:
            zip_path: Path to a zip created by export_profile().

        Returns:
            The newly created profile dict.
        """
        import tempfile

        with zipfile.ZipFile(zip_path, "r") as zf:
            with tempfile.TemporaryDirectory() as tmp:
                zf.extractall(tmp)
                manifest_path = os.path.join(tmp, "manifest.json")
                with open(manifest_path) as f:
                    manifest = json.load(f)

                pdata = manifest["profile"]
                profile = self.db.create_profile(pdata["name"], pdata.get("description", ""))
                profile_id = profile["id"]
                profile_dir = self.db.get_profile_dir(profile_id)
                audio_dir = os.path.join(profile_dir, "audio")
                emb_dir   = os.path.join(profile_dir, "embeddings")
                mel_dir   = os.path.join(profile_dir, "prompt")
                os.makedirs(audio_dir, exist_ok=True)
                os.makedirs(emb_dir,   exist_ok=True)
                os.makedirs(mel_dir,   exist_ok=True)

                for af_info in manifest.get("audio_files", []):
                    audio_src = os.path.join(tmp, "audio", af_info["audio_file"]) if af_info.get("audio_file") else None
                    emb_src   = os.path.join(tmp, "embeddings", af_info["embedding_file"]) if af_info.get("embedding_file") else None
                    mel_src   = os.path.join(tmp, "prompt", af_info["mel_file"]) if af_info.get("mel_file") else None

                    audio_dst = os.path.join(audio_dir, af_info["audio_file"]) if audio_src else None
                    emb_dst   = os.path.join(emb_dir,   af_info["embedding_file"]) if emb_src else None
                    mel_dst   = os.path.join(mel_dir,   af_info["mel_file"]) if mel_src else None

                    if audio_src and os.path.isfile(audio_src) and audio_dst:
                        shutil.copy2(audio_src, audio_dst)
                    if emb_src and os.path.isfile(emb_src) and emb_dst:
                        shutil.copy2(emb_src, emb_dst)
                    if mel_src and os.path.isfile(mel_src) and mel_dst:
                        shutil.copy2(mel_src, mel_dst)

                    self.db.add_audio_file(
                        profile_id=profile_id,
                        filename=af_info["filename"],
                        file_path=audio_dst or "",
                        duration=af_info.get("duration", 0),
                        embedding_path=emb_dst,
                        mel_path=mel_dst,
                        is_default=bool(af_info.get("is_default")),
                    )

        logger.info(f"[profile_manager] Imported profile '{manifest['profile']['name']}' as {profile_id}")
        return self.db.get_profile(profile_id)


# Singleton instance
_manager = None


def get_profile_manager() -> ProfileManager:
    """Get profile manager singleton."""
    global _manager
    if _manager is None:
        _manager = ProfileManager()
    return _manager


# ---------------------------------------------------------------------------
# QThread embedding worker
# ---------------------------------------------------------------------------

try:
    from PySide6.QtCore import QThread, Signal as _Signal

    class EmbeddingWorker(QThread):
        """Background worker for audio upload + WavLM embedding extraction.

        Signals:
            progress(int):     0, 50, 100
            finished(dict):    The created audio_file dict.
            error(str):        Error message on failure.
        """

        progress = _Signal(int)
        finished = _Signal(dict)
        error    = _Signal(str)

        def __init__(
            self,
            profile_id: str,
            source_path: str,
            is_default: bool = False,
            device: str = "cpu",
            parent=None,
        ) -> None:
            super().__init__(parent)
            self._profile_id   = profile_id
            self._source_path  = source_path
            self._is_default   = is_default
            self._device       = device

        def run(self) -> None:
            try:
                self.progress.emit(0)
                pm = get_profile_manager()
                self.progress.emit(10)
                audio_file = pm.add_audio(
                    self._profile_id,
                    self._source_path,
                    is_default=self._is_default,
                    device=self._device,
                )
                self.progress.emit(100)
                self.finished.emit(audio_file)
            except Exception as exc:
                logger.error(f"[EmbeddingWorker] failed: {exc}", exc_info=True)
                self.error.emit(str(exc))

except ImportError:
    # PySide6 not available (unit-test context)
    EmbeddingWorker = None  # type: ignore[assignment,misc]

