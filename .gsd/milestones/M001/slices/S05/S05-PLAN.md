# S05: Offline Page — End-to-End File Conversion

**Goal:** Complete the Offline page: profile picker, source file selector, steps slider, output directory, real conversion via engine.convert() in a QThread, real progress signals, output waveform preview, play/stop via QMediaPlayer.
**Demo:** Convert anchor_converted.wav with Trump profile → hear Trump voice in output.

## Must-Haves

- Conversion produces real audio; waveform rendered; play/stop works; error shown on missing asset; cancellation stops worker cleanly.

## Proof Level

- This slice proves: Select profile + wav + click Convert → non-empty wav in output_dir; play button plays it; progress reaches 100%.

## Integration Closure

Receives current_profile from app signal. Output path passed to Analysis page via signal.

## Verification

- Progress signals at BN/spk/inference/vocoder phases; RTF logged after completion.

## Tasks

- [x] **T01: ConversionWorker with cancellation support** `est:30m`
  1. ConversionWorker(QThread): signals progress(int, str), finished(str), error(str).
2. progress_cb passed to engine.convert() — emits signal at 0 ('Extracting content...'), 33 ('Extracting speaker...'), 66 ('Running inference...'), 100 ('Saving output...').
3. Worker stores a _cancelled flag; check between phases.
4. Worker.cancel(): sets _cancelled=True.
5. Engine.convert() accepts optional cancellation check callback.
  - Files: `meanvc_gui/core/engine.py`, `meanvc_gui/pages/offline.py`
  - Verify: python -c 'from meanvc_gui.pages.offline import ConversionWorker; print("worker OK")'

- [x] **T02: Rewrite offline.py with end-to-end conversion UI** `est:1.5h`
  Rewrite meanvc_gui/pages/offline.py:
1. Header: 'Offline Conversion' title.
2. Profile picker: QComboBox populated from DB profiles; refreshed when app.current_profile_changed fires; if app.current_profile is set, pre-select it.
3. Source file row: path field + Browse button + drag-drop.
4. Output directory row: path field + Browse button (default: project root/meanvc_out/).
5. Settings card: Steps slider 1-4 + label; model size label (200ms only for now).
6. Convert button (primary) + Cancel button (secondary, disabled until running).
7. Progress bar with phase label below it.
8. Result card (hidden until done): output path label + waveform image + Play / Stop buttons using QMediaPlayer.
9. 'Send to Analysis' button (secondary) — emits signal with output path to app.
  - Files: `meanvc_gui/pages/offline.py`
  - Verify: python -c 'from meanvc_gui.pages.offline import OfflinePage; print("offline import OK")'

## Files Likely Touched

- meanvc_gui/core/engine.py
- meanvc_gui/pages/offline.py
