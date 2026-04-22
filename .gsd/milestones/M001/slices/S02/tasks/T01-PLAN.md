---
estimated_steps: 9
estimated_files: 1
skills_used: []
---

# T01: Rewrite theme.py with complete design system

Rewrite meanvc_gui/components/theme.py to include:
1. COLORS dict with full palette: background (#09090b), surface (#18181b), surface_variant (#27272a), primary (#06b6d4 - shifted to slightly warmer cyan), secondary (#a78bfa), text/text_secondary/text_muted, success/warning/error, border.
2. get_dark_palette() → QPalette (already exists, keep).
3. get_stylesheet() → full QSS string covering QMainWindow, QWidget, QGroupBox, QLabel, QLineEdit, QPushButton (normal + :hover + :pressed + :disabled), QPushButton[primary='true'] accent style, QComboBox, QSlider, QProgressBar, QListWidget, QTableWidget, QScrollBar, QSplitter, QCheckBox.
4. CardFrame class (QFrame subclass) with rounded border + background.
5. PrimaryButton class (QPushButton subclass) with accent color.
6. SecondaryButton class (QPushButton subclass) with outlined style.
7. SectionTitle class (QLabel subclass) with 24px weight-300.
8. PageContainer class (QWidget subclass) with standard 24px margins.

## Inputs

- `meanvc_gui/components/theme.py`

## Expected Output

- `theme.py exports COLORS, get_stylesheet, CardFrame, PrimaryButton, SecondaryButton, SectionTitle, PageContainer`

## Verification

python -c 'from meanvc_gui.components.theme import COLORS, get_stylesheet, CardFrame, PrimaryButton; print("theme OK")'
