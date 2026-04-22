---
estimated_steps: 9
estimated_files: 1
skills_used: []
---

# T01: Implement VCRunner QThread from run_rt.py

1. Create meanvc_gui/core/vc_runner.py containing VCRunner(QThread):
   - Ports the run_rt.py inference loop verbatim but replaces sounddevice callbacks with ring buffer approach.
   - __init__(profile_id, input_device_idx, output_device_idx, steps, save_path=None)
   - Uses engine singleton to get loaded models (no model loading in runner — engine must already be loaded).
   - Runs sounddevice InputStream + OutputStream callbacks writing to/reading from ring buffers.
   - Inference loop in QThread.run(): read from input ring, process, write to output ring.
   - Emits: chunk_rtf(float), status(str), error(str), underrun(int).
   - stop(): sets _stop flag; waits for thread to join cleanly.
2. save_path: if set, accumulate output wav chunks, save on stop().

## Inputs

- `src/runtime/run_rt.py`
- `meanvc_gui/core/engine.py`

## Expected Output

- `vc_runner.py with VCRunner class that ports run_rt.py inference loop`

## Verification

python -c 'from meanvc_gui.core.vc_runner import VCRunner; print("vc_runner OK")'
