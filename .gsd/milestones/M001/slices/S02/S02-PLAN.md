# S02: Design System — Single Professional Theme

**Goal:** Build one authoritative theme module with a professional dark color system, reusable card/button/input CSS, and a consistent main window layout. Every page will import only from this module.
**Demo:** Navigate all five pages; every page looks intentionally designed and visually consistent.

## Must-Haves

- Single theme.py; consistent sidebar + page headers; no inline color strings in page files; all pages importable without error.

## Proof Level

- This slice proves: Visual: all five pages render consistently. Code: rg '#[0-9a-fA-F]{6}' meanvc_gui/pages/ returns zero matches.

## Integration Closure

All pages import COLORS, get_stylesheet(), CardFrame, PrimaryButton from meanvc_gui/components/theme.py. No inline hex strings in page files.

## Verification

- None.

## Tasks

- [x] **T01: Rewrite theme.py with complete design system** `est:1h`
  Rewrite meanvc_gui/components/theme.py to include:
1. COLORS dict with full palette: background (#09090b), surface (#18181b), surface_variant (#27272a), primary (#06b6d4 - shifted to slightly warmer cyan), secondary (#a78bfa), text/text_secondary/text_muted, success/warning/error, border.
2. get_dark_palette() → QPalette (already exists, keep).
3. get_stylesheet() → full QSS string covering QMainWindow, QWidget, QGroupBox, QLabel, QLineEdit, QPushButton (normal + :hover + :pressed + :disabled), QPushButton[primary='true'] accent style, QComboBox, QSlider, QProgressBar, QListWidget, QTableWidget, QScrollBar, QSplitter, QCheckBox.
4. CardFrame class (QFrame subclass) with rounded border + background.
5. PrimaryButton class (QPushButton subclass) with accent color.
6. SecondaryButton class (QPushButton subclass) with outlined style.
7. SectionTitle class (QLabel subclass) with 24px weight-300.
8. PageContainer class (QWidget subclass) with standard 24px margins.
  - Files: `meanvc_gui/components/theme.py`
  - Verify: python -c 'from meanvc_gui.components.theme import COLORS, get_stylesheet, CardFrame, PrimaryButton; print("theme OK")'

- [x] **T02: Rewrite main.py with polished sidebar navigation** `est:45m`
  Rewrite meanvc_gui/main.py:
1. Use QStackedWidget for page switching (not show/hide pattern).
2. Sidebar: fixed 200px, dark bg, app logo/title at top, nav items with icon + label, active state uses primary color left-border + background highlight.
3. Nav items: Library (book icon), Realtime (mic), Offline (file), Analysis (chart), Settings (gear) — use Unicode emoji or text icons.
4. Bottom of sidebar: device badge (CUDA/MPS/CPU) and app version.
5. Content area: QStackedWidget, pages pushed at init.
6. Apply get_stylesheet() globally.
7. Startup: check assets missing flag from engine; if missing, show settings page first.
8. Cross-page profile signal: app.current_profile_changed = Signal(dict) — emitted when Library sets profile.
  - Files: `meanvc_gui/main.py`
  - Verify: python -m meanvc_gui.main &; sleep 3; kill %1; echo 'launched OK'

## Files Likely Touched

- meanvc_gui/components/theme.py
- meanvc_gui/main.py
