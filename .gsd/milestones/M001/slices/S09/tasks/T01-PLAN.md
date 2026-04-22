---
estimated_steps: 11
estimated_files: 4
skills_used: []
---

# T01: Cross-page integration and startup flow

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

## Inputs

- `meanvc_gui/main.py`
- `meanvc_gui/pages/offline.py`

## Expected Output

- `Cross-page profile sync works`
- `Keyboard shortcuts registered`
- `Startup asset check shows info bar`

## Verification

python -c 'from meanvc_gui.main import MeanVCWindow; print("main import OK")'
