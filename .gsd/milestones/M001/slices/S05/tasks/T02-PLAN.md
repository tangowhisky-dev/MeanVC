---
estimated_steps: 10
estimated_files: 1
skills_used: []
---

# T02: Rewrite offline.py with end-to-end conversion UI

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

## Inputs

- `meanvc_gui/pages/offline.py`
- `meanvc_gui/components/theme.py`
- `meanvc_gui/core/engine.py`

## Expected Output

- `offline.py fully functional end-to-end`

## Verification

python -c 'from meanvc_gui.pages.offline import OfflinePage; print("offline import OK")'
