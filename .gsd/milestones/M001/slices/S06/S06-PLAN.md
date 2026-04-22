# S06: Realtime Page — Live Mic-to-Speaker Conversion

**Goal:** Complete the Realtime page: port VCRunner loop from run_rt.py into a QThread worker, wire to sounddevice I/O, live waveform via QLineSeries, profile picker, steps control, save-to-file toggle.
**Demo:** Speak into mic → hear converted voice; waveform animates; RTF label shows < 1.0.

## Must-Haves

- VCRunner starts/stops cleanly; converted audio plays from output device; waveform updates; RTF shown; save-to-file produces wav.

## Proof Level

- This slice proves: Start with test profile → mic audio plays back as converted voice; RTF < 1.0 on CUDA/MPS; Stop cleanly terminates streams.

## Integration Closure

Uses engine singleton loaded by S03. Reads profiles from app.current_profile.

## Verification

- RTF per chunk logged to console; under-run counter shown in UI status bar.

## Tasks

- [x] **T01: Implement VCRunner QThread from run_rt.py** `est:2h`
  1. Create meanvc_gui/core/vc_runner.py containing VCRunner(QThread):
   - Ports the run_rt.py inference loop verbatim but replaces sounddevice callbacks with ring buffer approach.
   - __init__(profile_id, input_device_idx, output_device_idx, steps, save_path=None)
   - Uses engine singleton to get loaded models (no model loading in runner — engine must already be loaded).
   - Runs sounddevice InputStream + OutputStream callbacks writing to/reading from ring buffers.
   - Inference loop in QThread.run(): read from input ring, process, write to output ring.
   - Emits: chunk_rtf(float), status(str), error(str), underrun(int).
   - stop(): sets _stop flag; waits for thread to join cleanly.
2. save_path: if set, accumulate output wav chunks, save on stop().
  - Files: `meanvc_gui/core/vc_runner.py`
  - Verify: python -c 'from meanvc_gui.core.vc_runner import VCRunner; print("vc_runner OK")'

- [x] **T02: Rewrite realtime.py wired to VCRunner** `est:1.5h`
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
  - Files: `meanvc_gui/pages/realtime.py`
  - Verify: python -c 'from meanvc_gui.pages.realtime import RealtimePage; print("realtime import OK")'

## Files Likely Touched

- meanvc_gui/core/vc_runner.py
- meanvc_gui/pages/realtime.py
