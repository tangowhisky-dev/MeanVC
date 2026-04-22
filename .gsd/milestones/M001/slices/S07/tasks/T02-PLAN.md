---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T02: Rewrite analysis.py with real similarity chart

Rewrite meanvc_gui/pages/analysis.py:
1. Two file pickers (File A: reference, File B: converted) with Browse buttons and drag-drop.
2. 'Receive from Offline' button: populated automatically when Offline emits output_ready signal.
3. Analyze button → SimilarityWorker.
4. Results card: QCharts horizontal bar showing File A score vs File B score (0-100).
5. Score label: big number with colour (green > 70, amber 40-70, red < 40).
6. Detail table: Similarity %, Duration A/B, Quality A/B.
7. Loading spinner while worker runs.

## Inputs

- `meanvc_gui/pages/analysis.py`
- `meanvc_gui/components/theme.py`
- `meanvc_gui/core/engine.py`

## Expected Output

- `analysis.py fully wired to real similarity engine`

## Verification

python -c 'from meanvc_gui.pages.analysis import AnalysisPage; print("analysis import OK")'
