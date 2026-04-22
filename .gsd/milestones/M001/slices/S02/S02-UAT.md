# S02: Design System — Single Professional Theme — UAT

**Milestone:** M001
**Written:** 2026-04-22T10:03:56.177Z

## S02 UAT

1. `python -c 'from meanvc_gui.components.theme import COLORS, get_stylesheet, CardFrame, PrimaryButton, StatusBadge'` → OK
2. `python -c 'from meanvc_gui.main import MeanVCWindow, bus'` → OK
3. `python -m meanvc_gui.main` → Window opens with sidebar showing Library/Realtime/Offline/Analysis/Settings nav items, device badge at bottom
4. `rg '#[0-9a-fA-F]{6}' meanvc_gui/pages/ --include='*.py' -l` → ideally zero (will complete in later slices as pages are rewritten)
