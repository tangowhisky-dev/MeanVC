# KNOWLEDGE — MeanVC

Append-only register of project-specific rules, patterns, and lessons learned.
Read at the start of every unit. Never remove or edit existing entries.

---

## Architecture

### Zero-shot — no training loop
MeanVC requires no per-profile training. The entire conversion pipeline is:
`source audio → BN features (FastU2++) → DiT flow model → Vocos → wav`
with a speaker embedding + prompt mel from the reference audio.
There is no `G_latest.pth`, no epoch loop, no discriminator.

### Three TorchScript models at runtime
All three are loaded via `torch.jit.load()`:
- `assets/ckpt/meanvc_200ms.pt` — DiT VC model (safetensors alt: `model_200ms.safetensors`)
- `assets/ckpt/vocos.pt` — Vocos vocoder
- `assets/ckpt/fastu2++.pt` — FastU2++ streaming ASR (BN feature extractor)
Plus one nn.Module: WavLM ECAPA-TDNN (`assets/wavLM/wavlm_large_finetune.pth`)

### Audio sample rate is always 16kHz
All models operate at 16kHz. Mel hop = 160 samples = 10ms. Chunk = 3200 samples = 200ms.
Resample everything to 16kHz before any feature extraction.

### Mel spectrogram is custom, not torchaudio's
`MelSpectrogramFeatures` in `src/utils/audio.py` uses `librosa_mel_fn` filterbank +
`torch.stft(return_complex=True)`. Do not substitute `torchaudio.transforms.MelSpectrogram`
— it uses different filterbank values and will break loaded checkpoints.

### BN extraction is chunk-wise streaming
FastU2++ uses `forward_encoder_chunk()` with a sliding window (decoding_chunk_size=5,
stride=20, context=7, subsampling=4). Output is upsampled 4× by linear interpolation
to match mel frame rate.

### KV-cache bounded at 100 frames
During inference, kv_cache is trimmed to last `C_KV_CACHE_MAX_LEN=100` frames when
offset > 40. Without this, memory grows quadratically for long audio.

### Speaker embedding capped at 10s, prompt mel capped at 500 frames
WavLM-Large uses O(T²) relative attention — long audio (>10s) causes OOM.
`SV_MAX_SECS=10`, `PROMPT_MAX_FRAMES=500` are hard caps in `convert.py`.

---

## Profile System

### Profiles are reference audio collections, not trained models
A profile = set of WAV files + pre-extracted WavLM embeddings + prompt mel.
Export/import = zip of audio files + embeddings + manifest.json (no checkpoint files needed).

### Pre-extract embeddings on audio upload
At upload time: run WavLM ECAPA-TDNN → save `embeddings/{file_id}.pt` (shape [1, 256]).
At inference time: load `.pt` directly — do not re-run WavLM on every conversion.

### Default prompt mel = first/best audio file
When user does not specify a prompt, use the first uploaded audio file's mel.
Store `is_default INTEGER` in audio_files table to track which file is the default prompt.

### Profile storage is tiny vs rvc-web
rvc-web: ~400-500MB per profile (checkpoint files).
MeanVC: ~10-50MB per profile (audio files + small .pt tensors).
No size pressure — can afford to keep full original WAVs.

---

## Realtime Pipeline

### Chunk size = 3200 samples (200ms)
`CHUNK = 160 * stride` where stride = `subsampling * decoding_chunk_size = 4 * 5 = 20`.
BN output per chunk = 5 frames. VC output = 20 mel frames. Vocoder output = 3200 samples.

### Overlap-add at vocoder boundary
`vocoder_overlap=3` frames, `vocoder_wav_overlap = (3-1)*160 = 320` samples.
Cross-fade with `up_linspace`/`down_linspace` numpy arrays to avoid click artifacts.

### sounddevice callback must be non-blocking
All heavy processing (BN extraction, DiT inference, vocoder) runs in a background thread.
The sounddevice callback only reads from/writes to a ring buffer. Never block the callback.

### Steps=1 or steps=2 for realtime
steps=1: `timesteps=[1.0, 0.0]` — fastest, acceptable quality.
steps=2: `timesteps=[1.0, 0.8, 0.0]` — balanced, default.
steps>2: only for offline; RTF > 1.0 on most hardware.

---

## PySide6 GUI

PySide6 (Qt6) was chosen over Flet due to more available expertise and richer widget set (QCharts, QMediaPlayer, QPainter-based waveform). All GUI code uses PySide6 exclusively.

### Heavy work must use QThread
Pages dispatch inference/embedding work via `QThread` subclasses (see `ConversionWorker`
in `offline.py`). Never call model.forward() on the Qt event loop — it freezes the UI.

### Qt signals/slots for cross-thread updates
Worker threads emit Qt signals (`progress`, `finished`, `error`) that connect to UI slots.

### Audio playback via QMediaPlayer (Qt6 multimedia)
For file playback, use `QMediaPlayer`. For realtime monitoring, use sounddevice directly.

### Analysis page uses QCharts (PySide6-Addons)
`analysis.py` imports `QChart`, `QChartView`, `QBarSeries` from `PySide6.QtCharts`.
Requires `PySide6-Addons` in the GUI requirements.

### DB location is project-root data/, not meanvc_gui/data/
`profile_db.py` uses three levels of dirname from `__file__` to resolve project root.
DB file: `data/meanvc.db`. Profiles dir: `data/profiles/`. Both gitignored.
`meanvc_gui/data/meanvc.db`, not `data/meanvc.db` at the repo root.

---

## Asset Management

### download_ckpt.py handles all downloads
HuggingFace core models via `hf_hub_download`. WavLM via gdown (Google Drive).
Run `python download_ckpt.py --verify` to check asset status without downloading.

### wavlm_large_finetune.pth is the only manual download
All other assets are automated. This file requires gdown from Google Drive.
GDrive ID: `1-aE1NfzpRCLxA4GUxX9ITI3F9LlbtEGP`. Destination: `assets/wavLM/`.

### Asset check before model load
Check all 5 required files exist before attempting `torch.jit.load()`.
Missing checkpoint → cryptic `RuntimeError` deep in TorchScript. Fail early with clear message.

---

## Lessons from rvc-web (directly applicable)

### Never parse subprocess stdout for progress
rvc-web lesson: long tqdm lines crash asyncio StreamReader (64KB limit).
MeanVC: no subprocess training loop, but if any subprocess is added later,
redirect stdout to a log file and track progress via DB or file polling.

### Silent exception swallowing causes "0 results" bugs
rvc-web lesson: `except Exception: continue` in preprocessing hid torchaudio load errors.
MeanVC: always log exceptions with `logger.error(msg, exc_info=True)` before continuing.

### WAV PCM-16 for all saved outputs
rvc-web lesson: consistent format avoids downstream playback surprises.
MeanVC: all saved conversions use `torchaudio.save(path, wav, 16000)` (WAV PCM float32).
If PCM-16 is needed: `sf.write(path, wav.numpy().T, 16000, subtype="PCM_16")`.

### Speaker embedding cap prevents OOM
rvc-web lesson: no cap on reference audio → WavLM OOM on long files.
MeanVC: already capped at 10s (`SV_MAX_SECS=10`) in `convert.py`. Keep this in the GUI too.

### aarch64 PyTorch: lfilter/conv1d Xbyak bug
Skip any `torchaudio.functional.lfilter` calls on aarch64 Linux.
Augmentation code paths must check `platform.machine() in ("aarch64", "arm64")`.

### torchcodec required on aarch64 for torchaudio.load
`torchaudio.load` on aarch64 Linux falls back to torchcodec backend.
Add `torchcodec` to requirements. Without it: `ImportError: TorchCodec is required`.

### uv venv at ~/.meanvc, not conda
Use `uv venv ~/.meanvc --python 3.11`. No conda dependency (licensing concerns).
install.sh: `VIRTUAL_ENV=~/.meanvc uv pip install ...`
start.sh: check conda `meanvc` env first, then fall back to `~/.meanvc`.

### Profile import/export: zip manifest v1
rvc-web export format: `manifest.json` + `audio/` + model files.
MeanVC equivalent: `manifest.json` + `audio/` + `embeddings/` + `prompt/`.
No checkpoint files in the zip (shared base model, not per-profile).

### DB migrations via _MIGRATIONS list
rvc-web lesson: schema changes without migrations cause column-not-found errors.
Pattern: `_MIGRATIONS = [("ALTER TABLE ...", ), ...]` with `IF NOT EXISTS` checks.
Run at DB init time.

### ECAPA-TDNN for similarity analysis (same model as rvc-web)
rvc-web uses ECAPA-TDNN (`assets/ecapa/ecapa_tdnn.pt`) for speaker similarity.
MeanVC can reuse the same approach — compare converted output vs reference embedding.
Similarity = cosine similarity between two ECAPA embeddings, mapped to 0–100%.
