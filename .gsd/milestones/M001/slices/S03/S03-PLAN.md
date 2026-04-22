# S03: Core Engine — Real Inference Wired

**Goal:** Replace engine.py stub with a working inference singleton. Fix profile_manager.py WavLM path. Expose a clean API: load(), convert(), calculate_similarity(), and a check_assets() utility that all pages can query.
**Demo:** python -c "from meanvc_gui.core.engine import get_engine; e=get_engine(); print(e.loaded)" prints True after model load.

## Must-Haves

- Engine loads all four models once; convert() returns real wav path; missing assets raises AssetsMissingError; profile_manager uses correct WavLM path.

## Proof Level

- This slice proves: python convert.py --source X --reference Y --output Z produces real wav; engine.convert() from REPL returns path to non-empty file.

## Integration Closure

S04-S07 all call engine methods. S08 calls check_assets().

## Verification

- Engine logs model load durations and RTF per conversion to stderr with structured prefixes.

## Tasks

- [x] **T01: Implement engine.py model loading and asset check** `est:1.5h`
  1. Define REQUIRED_ASSETS dict: name → path for all 5 required files (model_config, dit_ckpt, vocos_ckpt, asr_ckpt, sv_ckpt).
2. Define AssetsMissingError(RuntimeError) that lists missing files.
3. Implement check_assets() → dict: {name: {path, exists, size_mb}}.
4. Implement _load_models(device) that:
   - Loads DiT from safetensors + model config (from convert.py pattern)
   - Loads Vocos via torch.jit.load()
   - Loads FastU2++ via torch.jit.load()
   - Loads WavLM ECAPA-TDNN via init_sv_model('wavlm_large', sv_ckpt)
   - Builds MelSpectrogramFeatures
   - Returns dict of all models
5. Singleton pattern: _ENGINE = None; get_engine(device='auto') creates on first call.
6. Engine.load() calls check_assets() first; raises AssetsMissingError if any missing.
7. Engine.is_loaded property.
8. All model-loading code extracted from convert.py, not copy-pasted — import shared helpers from src/.
  - Files: `meanvc_gui/core/engine.py`
  - Verify: python -c "from meanvc_gui.core.engine import check_assets; r=check_assets(); print({k: v['exists'] for k,v in r.items()})"

- [x] **T02: Implement Engine.convert() using convert.py logic** `est:1h`
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
  - Files: `meanvc_gui/core/engine.py`
  - Verify: python -c "
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

- [x] **T03: Fix profile_manager.py WavLM path and mel extractor** `est:45m`
  1. Fix extract_wavlm_embedding() in profile_manager.py:
   - Remove the wrong WavLM(cfg_path=..., ckpt_path=...) call.
   - Use init_sv_model('wavlm_large', sv_ckpt_path) from src/runtime/speaker_verification/verification.py.
   - sv_ckpt_path = os.path.join(PROJECT_ROOT, 'assets', 'wavLM', 'wavlm_large_finetune.pth').
   - Cap input audio at SV_MAX_SECS=10 before running.
   - Output embedding shape must be [1, 256].
2. Fix extract_mel_spectrogram() to use MelSpectrogramFeatures from src/utils/audio.py instead of torchaudio.transforms.MelSpectrogram (different filterbank!).
3. Remove unused aiofiles import.
4. Add logging for embedding extraction (duration, shape).
  - Files: `meanvc_gui/core/profile_manager.py`
  - Verify: python -c "
import sys, os, tempfile; sys.path.insert(0,'')
from meanvc_gui.core.profile_manager import extract_wavlm_embedding, extract_mel_spectrogram
with tempfile.TemporaryDirectory() as d:
    emb_ok = extract_wavlm_embedding('src/runtime/example/test.wav', os.path.join(d,'emb.pt'), device='cpu')
    print('embedding extracted:', emb_ok)
"

## Files Likely Touched

- meanvc_gui/core/engine.py
- meanvc_gui/core/profile_manager.py
