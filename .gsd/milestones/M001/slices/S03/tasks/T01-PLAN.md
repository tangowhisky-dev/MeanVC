---
estimated_steps: 14
estimated_files: 1
skills_used: []
---

# T01: Implement engine.py model loading and asset check

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

## Inputs

- `convert.py`
- `meanvc_gui/core/engine.py`
- `src/runtime/speaker_verification/verification.py`
- `src/utils/audio.py`

## Expected Output

- `engine.py has working load(), check_assets()`
- `AssetsMissingError imported by main.py for startup check`

## Verification

python -c "from meanvc_gui.core.engine import check_assets; r=check_assets(); print({k: v['exists'] for k,v in r.items()})"
