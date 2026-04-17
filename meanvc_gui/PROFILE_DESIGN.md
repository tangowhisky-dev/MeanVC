# MeanVC Profile Storage Design

## Overview

MeanVC uses zero-shot voice conversion - no per-profile training required. This document outlines the profile storage system.

## Key Difference from rvc-web

| Feature | rvc-web (RVC) | MeanVC (Zeroshot) |
|---------|---------------|-------------------|
| Training | Required per profile | Not needed |
| Checkpoints | G_latest.pth, D_latest.pth | None |
| Model files | model_infer.pth (~54MB) | Shared base model |
| FAISS index | Per-profile | None |
| Per-profile storage | ~400-500MB | ~10-50MB |

## What to Save Per Profile

### 1. Audio Files
- Original voice recordings (`.wav`)
- Multiple audio samples per profile supported
- Stored in: `data/profiles/{id}/audio/`

### 2. Speaker Embeddings (Key for Zeroshot)
- **WavLM embeddings** - extracted from audio files
- Stored as `.pt` files (numpy tensors)
- Shape: typically `[1, 768]` or `[1, 1024]` depending on model
- Used at inference time as `spk_emb`
- Stored in: `data/profiles/{id}/embeddings/`

### 3. Prompt/Mel Reference
- Preprocessed mel-spectrogram from reference audio
- Used for reference-based inference (`prompt_mel`)
- Stored in: `data/profiles/{id}/prompt/`

### 4. Profile Metadata (SQLite)
```sql
profiles:
  - id: TEXT PRIMARY KEY
  - name: TEXT NOT NULL
  - created_at: TEXT NOT NULL
  - updated_at: TEXT NOT NULL
  - description: TEXT
  - embedding_model: TEXT  -- "wavlm" or "ecapa"
  - total_audio_duration: REAL  -- seconds
  - num_audio_files: INTEGER

audio_files:
  - id: TEXT PRIMARY KEY
  - profile_id: TEXT FK
  - filename: TEXT
  - file_path: TEXT
  - duration: REAL
  - embedding_path: TEXT  -- path to extracted embedding
  - created_at: TEXT
```

## Directory Structure

```
data/
├── meanvc.db              # SQLite database
└── profiles/
    └── {profile_id}/
        ├── manifest.json          # Profile metadata
        ├── audio/
        │   ├── voice1.wav
        │   ├── voice2.wav
        │   └── ...
        ├── embeddings/
        │   ├── voice1.pt         # WavLM embedding
        │   ├── voice1_mel.npy    # Mel spectrogram
        │   └── ...
        └── prompt/
            └── reference_mel.npy  # Default prompt mel
```

## Inference Pipeline Integration

MeanVC inference requires:
1. `spk_emb` - Speaker embedding tensor (from profile)
2. `prompt_mel` - Prompt mel-spectrogram (from profile)
3. `bn_path` - Batch normalization file (shared across profiles)

For zero-shot, the profile provides:
- Pre-extracted `spk_emb` to avoid repeated embedding computation
- Reference audio/mel for prompt-based inference

## Implementation Plan

1. **Database Schema** (`db.py`)
   - Create profiles table with zero-shot relevant fields
   - Create audio_files table with embedding paths

2. **Profile Manager** (`profile_manager.py`)
   - CRUD operations for profiles
   - Audio file upload/clipping
   - Embedding extraction (using WavLM)
   - Health checks

3. **API Routes** (`profiles.py`)
   - POST /api/profiles - Create profile
   - GET /api/profiles - List profiles
   - GET /api/profiles/{id} - Get profile
   - DELETE /api/profiles/{id} - Delete profile
   - POST /api/profiles/{id}/audio - Add audio
   - GET /api/profiles/{id}/audio/{file_id} - Stream audio
   - DELETE /api/profiles/{id}/audio/{file_id} - Delete audio

4. **UI Integration**
   - Library page shows profiles
   - Add/remove audio from profiles
   - Select active profile for conversion
