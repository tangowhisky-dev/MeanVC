---
estimated_steps: 9
estimated_files: 1
skills_used: []
---

# T01: Implement real ECAPA cosine similarity in engine

1. Implement Engine.calculate_similarity(file_a, file_b) → dict:
   - Load each file via torchaudio.load, resample to 16kHz, cap at 10s.
   - Run sv_model (ECAPA-TDNN via init_sv_model) to get [1,256] embeddings.
   - Cosine similarity = F.cosine_similarity(emb_a, emb_b).item(), mapped to 0-100.
   - Also compute: duration_a, duration_b, rms_a, rms_b (basic quality proxy).
   - Return: {similarity: float, duration_a: float, duration_b: float, quality_a: str, quality_b: str}
2. quality_a/b: 'Good' if rms > -30dBFS else 'Low' (simple threshold).
3. Engine must already be loaded; if not, load it.
4. SimilarityWorker(QThread) with finished(dict), error(str) signals.

## Inputs

- `meanvc_gui/core/engine.py`
- `src/runtime/speaker_verification/verification.py`

## Expected Output

- `Engine.calculate_similarity returns real cosine score`
- `SimilarityWorker class exists`

## Verification

python -c "
import sys; sys.path.insert(0,'')
from meanvc_gui.core.engine import get_engine
e = get_engine()
if e.check_assets_ok():
    r = e.calculate_similarity('src/runtime/example/test.wav', 'src/runtime/example/test.wav')
    assert r['similarity'] > 90, f'Same-file similarity too low: {r}'
    print('similarity OK:', r['similarity'])
else:
    print('assets missing — skip')
"
