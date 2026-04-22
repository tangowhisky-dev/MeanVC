# S09: Polish, Integration, and README

**Goal:** Final integration pass: cross-page profile sync, startup flow, keyboard shortcuts, app icon, and README rewrite.
**Demo:** Full demo walkthrough: Library → Offline → Analysis → Realtime, all functional.

## Must-Haves

- Profile selected in Library visible in Offline/Realtime dropdowns; Ctrl+Q quits; README matches reality; no stub values anywhere.

## Proof Level

- This slice proves: Full user journey from fresh DB: create profile → upload audio → offline convert → view similarity → realtime (if hardware present); all steps work without navigation errors.

## Integration Closure

Final milestone state — all slices integrated.

## Verification

- Startup log lists device, DB path, loaded models.

## Tasks

- [x] **T01: Cross-page integration and startup flow** `est:1h`
  1. Add QApplication signal/slot bus for cross-page events:
   - app.profile_selected(profile_dict) — emitted by Library Use button
   - app.analysis_requested(output_path) — emitted by Offline 'Send to Analysis'
2. Offline and Realtime pages subscribe to profile_selected; refresh their profile comboboxes.
3. Analysis page subscribes to analysis_requested; pre-populates File B.
4. Add keyboard shortcuts: Ctrl+Q → quit, Ctrl+1..5 → switch pages.
5. Startup sequence in main.py:
   a. Create window.
   b. check_assets() — if missing, show non-blocking info bar at top of window.
   c. Start engine pre-load in background thread (so first conversion is fast).
6. Bottom-of-sidebar: show 'CUDA' / 'MPS' / 'CPU' badge and 'v0.1.0' version.
  - Files: `meanvc_gui/main.py`, `meanvc_gui/pages/offline.py`, `meanvc_gui/pages/realtime.py`, `meanvc_gui/pages/analysis.py`
  - Verify: python -c 'from meanvc_gui.main import MeanVCWindow; print("main import OK")'

- [x] **T02: Rewrite README.md** `est:30m`
  Rewrite README.md from scratch:
1. Header: title, badges (arXiv, HuggingFace, Demo).
2. Features list.
3. Getting Started:
   - Environment setup: conda OR uv venv (both options).
   - Download models: python download_ckpt.py (assets go to assets/ckpt/ and assets/wavLM/) — not src/ckpt/.
   - WavLM manual download with correct destination (assets/wavLM/).
4. CLI Usage: convert.py with examples.
5. Desktop App (PySide6): pip install -r meanvc_gui/requirements.txt; python -m meanvc_gui.main.
6. Feature overview table (Library, Offline, Realtime, Analysis, Settings).
7. Training section (existing content).
8. Citation, license, contact.
  - Files: `README.md`
  - Verify: grep -n 'src/ckpt\|meanvc_gui/data' README.md | wc -l | awk '{exit $1>0}'

## Files Likely Touched

- meanvc_gui/main.py
- meanvc_gui/pages/offline.py
- meanvc_gui/pages/realtime.py
- meanvc_gui/pages/analysis.py
- README.md
