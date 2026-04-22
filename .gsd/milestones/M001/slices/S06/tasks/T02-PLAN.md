---
estimated_steps: 10
estimated_files: 1
skills_used: []
---

# T02: Rewrite realtime.py wired to VCRunner

Rewrite meanvc_gui/pages/realtime.py:
1. Profile picker: QComboBox from DB; refreshed on app.current_profile_changed.
2. Audio devices section: input QComboBox, output QComboBox from enumerate_audio_devices().
3. Steps control: QSlider 1-2 (realtime caps at 2).
4. Start button (primary): loads engine if not loaded (shows 'Loading models...' disabled state), then creates VCRunner and starts it.
5. Stop button (secondary): calls runner.stop().
6. Status bar: RTF display ('RTF: 0.42'), under-run counter.
7. Waveform: QLineSeries updated from chunk_rtf signal or a QTimer reading ring buffer.
8. Save output: QCheckBox + file path selector — passed as save_path to VCRunner.
9. Handle VCRunner.error signal: show QMessageBox, reset to stopped state.

## Inputs

- `meanvc_gui/pages/realtime.py`
- `meanvc_gui/core/vc_runner.py`
- `meanvc_gui/components/theme.py`

## Expected Output

- `realtime.py fully wired to VCRunner`

## Verification

python -c 'from meanvc_gui.pages.realtime import RealtimePage; print("realtime import OK")'
