# PROJECT — MeanVC Desktop App

## What This Is

MeanVC is a lightweight zero-shot voice conversion desktop application. Unlike rvc-web (which requires per-profile training), MeanVC uses a single pre-trained DiT (Diffusion Transformer) model to convert any source speaker to any target speaker in real-time using only a reference audio clip.

The core model uses **mean flows** for single-step inference — producing high-quality conversions in 1–2 denoising steps rather than 20–50 DDPM steps.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | PySide6 (Qt6 Python bindings) || Inference | PyTorch, DiT + Vocos vocoder |
| Content features | FastU2++ ASR (TorchScript) — bottleneck features |
| Speaker embedding | WavLM-Large ECAPA-TDNN — zero-shot identity |
| Audio I/O | sounddevice (realtime), torchaudio/TorchCodec (offline) |
| Database | SQLite (sync, via sqlite3) |
| Assets | HuggingFace Hub + Google Drive (gdown) |

## Architecture

### Inference Pipeline (one-shot, no training)

```
Source audio
  └─► FastU2++ ASR ──► BN features [1, T*4, 256]
                                           │
Reference audio                            ▼
  └─► WavLM ECAPA-TDNN ──► spk_emb [1, 256]     ──► DiT flow model ──► mel [1, 80, T]
  └─► MelSpectrogramFeatures ──► prompt_mel [1, T, 80] ──┘                    │
                                                                               ▼
                                                                    Vocos vocoder ──► wav
```

### Chunk-wise streaming (realtime)
- CHUNK = 3200 samples (200ms at 16kHz)
- KV-cache trimmed to last 100 frames to bound memory
- Overlap-add at vocoder output boundary (3-frame overlap)

## Profile System

Zero-shot — no training required. A profile is:
- A set of reference audio files (WAV)
- Pre-extracted WavLM speaker embeddings (`.pt`) — avoids re-extraction at inference
- Pre-extracted prompt mel (`.npy`) — first/best audio file as default prompt
- SQLite metadata row

## Key Assets (required before first run)

| File | Source | Purpose |
|------|--------|---------|
| `assets/ckpt/meanvc_200ms.pt` | HuggingFace | DiT TorchScript model |
| `assets/ckpt/model_200ms.safetensors` | HuggingFace | DiT safetensors (training) |
| `assets/ckpt/vocos.pt` | HuggingFace | Vocos vocoder TorchScript |
| `assets/ckpt/fastu2++.pt` | HuggingFace | FastU2++ ASR TorchScript |
| `assets/wavLM/wavlm_large_finetune.pth` | Google Drive | WavLM ECAPA-TDNN SV model |

Download: `python download_ckpt.py`

## Directory Layout

```
MeanVC/
  assets/               ← model weights (gitignored)
    ckpt/               ← DiT, Vocos, ASR
    wavLM/              ← WavLM speaker verification
    ecapa/              ← ECAPA-TDNN (optional, for analysis)
  src/
    config/             ← config_160ms.json, config_200ms.json
    infer/              ← dit_kvcache.py, infer.py, infer_ref.py
    model/              ← DiT, CFM, trainer
    preprocess/         ← mel/BN/spk extraction scripts
    runtime/            ← run_rt.py (realtime), speaker_verification/
    utils/              ← audio.py (MelSpectrogramFeatures, get_device, load_wav)
    wavLM/              ← WavLM model code
  vocos/                ← Vocos vocoder source
  meanvc_gui/           ← Desktop app (PySide6 / Qt6)
    main.py             ← entry point (QApplication)
    main_enhanced.py    ← alternate enhanced entry point
    main_modern.py      ← alternate modern entry point (legacy)
    core/
      engine.py         ← inference wrapper (STUB — not yet wired)
      profile_db.py     ← SQLite profile CRUD (sync, sqlite3)
      profile_manager.py← audio upload + WavLM embedding extraction
      device.py         ← device detection (CUDA > MPS > CPU)
    pages/
      library.py        ← profile management UI
      enhanced_library.py ← redesigned library (active)
      offline.py        ← file conversion UI
      realtime.py       ← live conversion UI
      analysis.py       ← speaker similarity UI (QCharts)
      settings.py       ← device + asset management
    components/
      waveform.py       ← waveform PNG generator
      theme.py          ← base dark theme (COLORS, palettes)
      enhanced_theme.py ← enhanced theme with ThemeManager
      modern_theme.py   ← modern theme variant (legacy)
    data/
      meanvc.db         ← SQLite database
      profiles/         ← per-profile audio + embeddings
  convert.py            ← CLI conversion entry point
  download_ckpt.py      ← asset downloader (HuggingFace + gdown)
```

## Device Support

| Platform | Device | Notes |
|----------|--------|-------|
| macOS (Apple Silicon) | MPS | Supported, tested |
| Linux x86_64 | CUDA | Primary target |
| Linux aarch64 | CUDA | DGX Spark tested |
| Any | CPU | Fallback, slow |

Auto-detection: `MEANVC_DEVICE` env var → CUDA → MPS → CPU

## Current State

All pages functional. Engine wired to real models. Zero stub return values.

- Core inference pipeline: **working** (`convert.py`, `src/runtime/run_rt.py`, `engine.py`)
- PySide6 GUI: **complete** — all five pages fully implemented
- Profile DB: **working** at `data/meanvc.db`
- Embedding extraction: **working** via `EmbeddingWorker` QThread
- Offline conversion: **working** via `ConversionWorker` + `engine.convert()`
- Realtime: **VCRunner QThread implemented** — live test pending hardware
- Analysis: **real ECAPA cosine similarity** via `SimilarityWorker`
- Settings: **real asset check** + `DownloadWorker` subprocess
- Cross-page bus: **wired** — Library → Offline/Realtime profile sync; Offline → Analysis output path
- README: **rewritten** — accurate asset paths and complete documentation

## What Needs Building

1. **Engine wrapper** — wire `engine.py` to actual `convert.py` inference path
2. **Profile embedding extraction** — fix WavLM path in `profile_manager.py`, call on upload
3. **Library page** — full CRUD, audio upload, embedding status display
4. **Offline page** — profile picker → convert → playback
5. **Realtime page** — device picker, VCRunner integration, waveform display
6. **Analysis page** — real ECAPA-TDNN similarity (not stub 75.0)
7. **Asset check on startup** — check actual 5 asset files, show download button if missing
8. **Settings page** — real asset status from `download_ckpt.py --verify`
9. **install.sh / start.sh** — uv-based env setup, asset pre-check
10. **Consolidate** — pick one entry point (`main.py` or `main_enhanced.py`), retire redundant theme files
