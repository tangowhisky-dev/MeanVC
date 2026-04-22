# S03: Core Engine — Real Inference Wired — UAT

**Milestone:** M001
**Written:** 2026-04-22T10:15:32.193Z

## S03 UAT

1. `python -c "from meanvc_gui.core.engine import check_assets; print(check_assets())"` → dict with path/exists/size_mb per asset
2. `python -c "from meanvc_gui.core.engine import AssetsMissingError; e = AssetsMissingError(['foo']); print(str(e))"` → error message listing missing files
3. `python -c "from meanvc_gui.core.profile_manager import EmbeddingWorker"` → imports
4. `python -c "from meanvc_gui.core.profile_manager import extract_mel_spectrogram; import inspect; src=inspect.getsource(extract_mel_spectrogram); assert 'MelSpectrogramFeatures' in src"` → passes
5. With all assets present: `engine.convert(source, ref, steps=1)` produces non-empty wav
