---
estimated_steps: 9
estimated_files: 1
skills_used: []
---

# T02: Rewrite main.py with polished sidebar navigation

Rewrite meanvc_gui/main.py:
1. Use QStackedWidget for page switching (not show/hide pattern).
2. Sidebar: fixed 200px, dark bg, app logo/title at top, nav items with icon + label, active state uses primary color left-border + background highlight.
3. Nav items: Library (book icon), Realtime (mic), Offline (file), Analysis (chart), Settings (gear) — use Unicode emoji or text icons.
4. Bottom of sidebar: device badge (CUDA/MPS/CPU) and app version.
5. Content area: QStackedWidget, pages pushed at init.
6. Apply get_stylesheet() globally.
7. Startup: check assets missing flag from engine; if missing, show settings page first.
8. Cross-page profile signal: app.current_profile_changed = Signal(dict) — emitted when Library sets profile.

## Inputs

- `meanvc_gui/main.py`
- `meanvc_gui/components/theme.py`

## Expected Output

- `main.py uses QStackedWidget`
- `Sidebar has 5 nav items with active state styling`
- `App applies global stylesheet`

## Verification

python -m meanvc_gui.main &; sleep 3; kill %1; echo 'launched OK'
