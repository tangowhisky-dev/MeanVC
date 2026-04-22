---
estimated_steps: 10
estimated_files: 1
skills_used: []
---

# T02: Implement Engine.convert() using convert.py logic

1. Implement Engine.convert(source_path, ref_path, steps, output_dir, progress_cb) using the logic from convert.py:
   - extract_bn(source_path, asr_model, device)
   - extract_speaker_and_prompt(ref_path, sv_model, mel_extractor, device)
   - run_inference(dit_model, vocos, bn, spk_emb, prompt_mel, chunk_size, steps)
   - torchaudio.save() output to output_dir
   - progress_cb called with 0/33/66/100 at BN/spk/inference/vocoder phases
2. progress_cb is optional (default None).
3. Return output file path (str).
4. wrap in try/except; re-raise with context on failure.
5. Engine.convert() does NOT re-load models if already loaded.

## Inputs

- `convert.py`
- `meanvc_gui/core/engine.py`

## Expected Output

- `Engine.convert() returns path to real wav file`

## Verification

python -c "
import sys; sys.path.insert(0,'')
from meanvc_gui.core.engine import get_engine
e = get_engine()
if e.check_assets_ok():
    out = e.convert('src/runtime/example/test.wav', 'src/runtime/example/test.wav', steps=1, output_dir='/tmp/meanvc_test')
    import os; assert os.path.getsize(out) > 1000, 'output too small'
    print('convert OK:', out)
else:
    print('assets missing — skip live test')
"
