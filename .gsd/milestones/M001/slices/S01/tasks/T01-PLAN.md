---
estimated_steps: 7
estimated_files: 9
skills_used: []
---

# T01: Delete Flet files and redundant GUI files

1. Delete FLET_IMPLEMENTATION_PLAN.md from repo root.
2. Delete meanvc_gui/main_modern.py, meanvc_gui/main_enhanced.py.
3. Delete meanvc_gui/components/enhanced_theme.py, meanvc_gui/components/modern_theme.py.
4. Delete meanvc_gui/pages/enhanced_library.py.
5. Delete meanvc_gui/DESIGN.md, meanvc_gui/PROFILE_DESIGN.md.
6. Verify remaining files: main.py, components/theme.py, components/waveform.py, pages/(library|offline|realtime|analysis|settings).py, core/(engine|profile_db|profile_manager|device).py.
7. Fix any import in library.py that imports from modern_theme — update to use components/theme.py COLORS instead.

## Inputs

- `meanvc_gui/pages/library.py`
- `meanvc_gui/components/modern_theme.py`

## Expected Output

- `None of the deleted files exist on disk`
- `meanvc_gui/pages/library.py imports from meanvc_gui.components.theme`

## Verification

python -c 'from meanvc_gui.pages.library import LibraryPage' && echo OK
