"""MeanVC Profile Database Module.

SQLite database for storing voice profiles used in zero-shot inference.
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "meanvc.db")
PROFILES_ROOT = os.path.join(DATA_DIR, "profiles")


def _ensure_dirs():
    """Create data directories if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PROFILES_ROOT, exist_ok=True)


def _init_db():
    """Initialize database schema."""
    _ensure_dirs()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Profiles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            embedding_model TEXT DEFAULT 'wavlm',
            total_audio_duration REAL DEFAULT 0,
            num_audio_files INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # Audio files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audio_files (
            id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            duration REAL,
            embedding_path TEXT,
            mel_path TEXT,
            is_default INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    """Get SQLite connection."""
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Initialize on module import
_init_db()


class ProfileDB:
    """Profile database operations."""

    @staticmethod
    def create_profile(name: str, description: str = "") -> dict:
        """Create a new voice profile.

        Args:
            name: Profile name
            description: Optional description

        Returns:
            dict: Created profile data
        """
        profile_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()

        # Create profile directory
        profile_dir = os.path.join(PROFILES_ROOT, profile_id)
        os.makedirs(os.path.join(profile_dir, "audio"), exist_ok=True)
        os.makedirs(os.path.join(profile_dir, "embeddings"), exist_ok=True)
        os.makedirs(os.path.join(profile_dir, "prompt"), exist_ok=True)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO profiles (id, name, description, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (profile_id, name, description, now, now),
        )
        conn.commit()
        conn.close()

        return ProfileDB.get_profile(profile_id)

    @staticmethod
    def get_profile(profile_id: str) -> Optional[dict]:
        """Get profile by ID.

        Args:
            profile_id: Profile ID

        Returns:
            dict: Profile data or None
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        profile = dict(row)
        profile["audio_files"] = ProfileDB.get_audio_files(profile_id)
        return profile

    @staticmethod
    def list_profiles() -> list[dict]:
        """List all profiles.

        Returns:
            list: List of profile dicts
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        profiles = []
        for row in rows:
            profile = dict(row)
            profile["audio_files"] = ProfileDB.get_audio_files(profile["id"])
            profiles.append(profile)

        return profiles

    @staticmethod
    def update_profile(
        profile_id: str, name: str = None, description: str = None
    ) -> dict:
        """Update profile metadata.

        Args:
            profile_id: Profile ID
            name: New name (optional)
            description: New description (optional)

        Returns:
            dict: Updated profile
        """
        now = datetime.now(timezone.utc).isoformat()

        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        updates.append("updated_at = ?")
        params.append(now)
        params.append(profile_id)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()

        return ProfileDB.get_profile(profile_id)

    @staticmethod
    def delete_profile(profile_id: str) -> bool:
        """Delete profile and all associated files.

        Args:
            profile_id: Profile ID

        Returns:
            bool: Success
        """
        # Get profile to find directory
        profile = ProfileDB.get_profile(profile_id)
        if profile is None:
            return False

        # Delete from database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audio_files WHERE profile_id = ?", (profile_id,))
        cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        conn.commit()
        conn.close()

        # Delete profile directory
        profile_dir = os.path.join(PROFILES_ROOT, profile_id)
        import shutil

        if os.path.exists(profile_dir):
            shutil.rmtree(profile_dir)

        return True

    @staticmethod
    def add_audio_file(
        profile_id: str,
        filename: str,
        file_path: str,
        duration: float,
        embedding_path: str = None,
        mel_path: str = None,
        is_default: bool = False,
    ) -> dict:
        """Add audio file to profile.

        Args:
            profile_id: Profile ID
            filename: Original filename
            file_path: Path to audio file
            duration: Audio duration in seconds
            embedding_path: Path to embedding file
            mel_path: Path to mel spectrogram
            is_default: Set as default reference

        Returns:
            dict: Created audio file
        """
        file_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()

        conn = get_connection()
        cursor = conn.cursor()

        # If setting as default, unset other defaults
        if is_default:
            cursor.execute(
                "UPDATE audio_files SET is_default = 0 WHERE profile_id = ?",
                (profile_id,),
            )

        cursor.execute(
            """INSERT INTO audio_files 
               (id, profile_id, filename, file_path, duration, embedding_path, mel_path, is_default, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                file_id,
                profile_id,
                filename,
                file_path,
                duration,
                embedding_path,
                mel_path,
                1 if is_default else 0,
                now,
            ),
        )

        # Update profile stats
        cursor.execute(
            """UPDATE profiles SET 
               total_audio_duration = total_audio_duration + ?,
               num_audio_files = num_audio_files + 1,
               updated_at = ?
               WHERE id = ?""",
            (duration, now, profile_id),
        )

        conn.commit()
        conn.close()

        return ProfileDB.get_audio_file(file_id)

    @staticmethod
    def get_audio_file(file_id: str) -> Optional[dict]:
        """Get audio file by ID.

        Args:
            file_id: Audio file ID

        Returns:
            dict: Audio file data
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audio_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    @staticmethod
    def get_audio_files(profile_id: str) -> list[dict]:
        """Get all audio files for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            list: List of audio file dicts
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audio_files WHERE profile_id = ? ORDER BY is_default DESC, created_at ASC",
            (profile_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    @staticmethod
    def delete_audio_file(file_id: str) -> bool:
        """Delete audio file from profile.

        Args:
            file_id: Audio file ID

        Returns:
            bool: Success
        """
        audio_file = ProfileDB.get_audio_file(file_id)
        if audio_file is None:
            return False

        profile_id = audio_file["profile_id"]
        duration = audio_file["duration"] or 0

        # Delete file from disk
        if audio_file["file_path"] and os.path.exists(audio_file["file_path"]):
            os.remove(audio_file["file_path"])
        if audio_file["embedding_path"] and os.path.exists(
            audio_file["embedding_path"]
        ):
            os.remove(audio_file["embedding_path"])
        if audio_file["mel_path"] and os.path.exists(audio_file["mel_path"]):
            os.remove(audio_file["mel_path"])

        # Update database
        now = datetime.now(timezone.utc).isoformat()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audio_files WHERE id = ?", (file_id,))
        cursor.execute(
            """UPDATE profiles SET 
               total_audio_duration = MAX(0, total_audio_duration - ?),
               num_audio_files = MAX(0, num_audio_files - 1),
               updated_at = ?
               WHERE id = ?""",
            (duration, now, profile_id),
        )
        conn.commit()
        conn.close()

        return True

    @staticmethod
    def set_default_audio(file_id: str) -> bool:
        """Set audio file as default reference.

        Args:
            file_id: Audio file ID

        Returns:
            bool: Success
        """
        audio_file = ProfileDB.get_audio_file(file_id)
        if audio_file is None:
            return False

        profile_id = audio_file["profile_id"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE audio_files SET is_default = 0 WHERE profile_id = ?", (profile_id,)
        )
        cursor.execute("UPDATE audio_files SET is_default = 1 WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()

        return True

    @staticmethod
    def get_profile_dir(profile_id: str) -> str:
        """Get profile directory path.

        Args:
            profile_id: Profile ID

        Returns:
            str: Profile directory path
        """
        return os.path.join(PROFILES_ROOT, profile_id)
