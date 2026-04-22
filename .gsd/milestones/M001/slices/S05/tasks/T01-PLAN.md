---
estimated_steps: 5
estimated_files: 2
skills_used: []
---

# T01: ConversionWorker with cancellation support

1. ConversionWorker(QThread): signals progress(int, str), finished(str), error(str).
2. progress_cb passed to engine.convert() — emits signal at 0 ('Extracting content...'), 33 ('Extracting speaker...'), 66 ('Running inference...'), 100 ('Saving output...').
3. Worker stores a _cancelled flag; check between phases.
4. Worker.cancel(): sets _cancelled=True.
5. Engine.convert() accepts optional cancellation check callback.

## Inputs

- `meanvc_gui/core/engine.py`

## Expected Output

- `ConversionWorker emits progress with descriptive messages`

## Verification

python -c 'from meanvc_gui.pages.offline import ConversionWorker; print("worker OK")'
