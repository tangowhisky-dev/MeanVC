# S07: Analysis Page — Real Speaker Similarity

**Goal:** Replace the hardcoded 75.0 stub with real ECAPA-TDNN cosine similarity. Add quality metrics. Display in QCharts bar chart with colour-coded bands.
**Demo:** Compare converted output with original reference → see similarity score > 70%.

## Must-Haves

- Similarity from real ECAPA cosine; chart renders; colour band correct; duration and quality metrics in table.

## Proof Level

- This slice proves: Two identical files → similarity > 95%; clearly different speakers → < 40%.

## Integration Closure

Receives output path from Offline page signal. Independent of Realtime.

## Verification

- Similarity score and extraction time logged.

## Tasks

- [x] **T01: Implement real ECAPA cosine similarity in engine** `est:45m`
  1. Implement Engine.calculate_similarity(file_a, file_b) → dict:
   - Load each file via torchaudio.load, resample to 16kHz, cap at 10s.
   - Run sv_model (ECAPA-TDNN via init_sv_model) to get [1,256] embeddings.
   - Cosine similarity = F.cosine_similarity(emb_a, emb_b).item(), mapped to 0-100.
   - Also compute: duration_a, duration_b, rms_a, rms_b (basic quality proxy).
   - Return: {similarity: float, duration_a: float, duration_b: float, quality_a: str, quality_b: str}
2. quality_a/b: 'Good' if rms > -30dBFS else 'Low' (simple threshold).
3. Engine must already be loaded; if not, load it.
4. SimilarityWorker(QThread) with finished(dict), error(str) signals.
  - Files: `meanvc_gui/core/engine.py`
  - Verify: python -c "
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

- [x] **T02: Rewrite analysis.py with real similarity chart** `est:1h`
  Rewrite meanvc_gui/pages/analysis.py:
1. Two file pickers (File A: reference, File B: converted) with Browse buttons and drag-drop.
2. 'Receive from Offline' button: populated automatically when Offline emits output_ready signal.
3. Analyze button → SimilarityWorker.
4. Results card: QCharts horizontal bar showing File A score vs File B score (0-100).
5. Score label: big number with colour (green > 70, amber 40-70, red < 40).
6. Detail table: Similarity %, Duration A/B, Quality A/B.
7. Loading spinner while worker runs.
  - Files: `meanvc_gui/pages/analysis.py`
  - Verify: python -c 'from meanvc_gui.pages.analysis import AnalysisPage; print("analysis import OK")'

## Files Likely Touched

- meanvc_gui/core/engine.py
- meanvc_gui/pages/analysis.py
