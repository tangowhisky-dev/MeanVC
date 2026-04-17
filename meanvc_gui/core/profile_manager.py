"""MeanVC Profile Manager.

Handles voice profile creation, audio processing, and embedding extraction.
"""

import os
import numpy as np
import torch
import torchaudio
from typing import Optional
import uuid
import aiofiles

from meanvc_gui.core.profile_db import ProfileDB


def get_project_root():
    """Get project root directory."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_audio_duration(file_path: str) -> float:
    """Get audio file duration in seconds.

    Args:
        file_path: Path to audio file

    Returns:
        float: Duration in seconds
    """
    try:
        info = torchaudio.info(file_path)
        return info.num_frames / info.sample_rate
    except Exception:
        return 0.0


def extract_wavlm_embedding(
    audio_path: str, output_path: str, device: str = "cpu"
) -> bool:
    """Extract WavLM embedding from audio file.

    Args:
        audio_path: Path to input audio
        output_path: Path to save embedding (.pt file)
        device: Device to run model on

    Returns:
        bool: Success
    """
    try:
        # Import WavLM
        from src.wavLM.WavLM import WavLM

        # Load WavLM model
        wavlm_model = WavLM(
            cfg_path="src/wavLM/configs/wavlm_base.yaml",
            ckpt_path="src/wavLM/ckpts/wavlm_base.pt",
        ).to(device)
        wavlm_model.eval()

        # Load audio
        waveform, sr = torchaudio.load(audio_path)

        # Resample if needed
        if sr != 16000:
            waveform = torchaudio.functional.resample(waveform, sr, 16000)

        # Ensure mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Extract features
        with torch.no_grad():
            features = wavlm_model.extract_features(waveform.to(device))
            # Use last layer, take mean over time
            embedding = features[-1].mean(dim=1)  # [1, 1024]

        # Save embedding
        torch.save(embedding.cpu(), output_path)
        return True

    except Exception as e:
        print(f"Error extracting WavLM embedding: {e}")
        return False


def extract_mel_spectrogram(audio_path: str, output_path: str) -> bool:
    """Extract mel spectrogram from audio file.

    Args:
        audio_path: Path to input audio
        output_path: Path to save mel (.npy file)

    Returns:
        bool: Success
    """
    try:
        # Load audio
        waveform, sr = torchaudio.load(audio_path)

        # Resample if needed
        if sr != 16000:
            waveform = torchaudio.functional.resample(waveform, sr, 16000)

        # Ensure mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)

        # Compute mel spectrogram
        mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=16000, n_fft=1024, hop_length=256, n_mels=80
        ).eval()

        with torch.no_grad():
            mel = mel_transform(waveform)
            # Convert to log scale
            mel = torch.log(torch.clamp(mel, min=1e-5))

        # Save mel
        np.save(output_path, mel.numpy())
        return True

    except Exception as e:
        print(f"Error extracting mel spectrogram: {e}")
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


# Singleton instance
_manager = None


def get_profile_manager() -> ProfileManager:
    """Get profile manager singleton.

    Returns:
        ProfileManager: Profile manager instance
    """
    global _manager
    if _manager is None:
        _manager = ProfileManager()
    return _manager
