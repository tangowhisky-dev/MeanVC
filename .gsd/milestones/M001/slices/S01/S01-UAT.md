# S01: Codebase Cleanup — Remove Flet, Consolidate Files — UAT

**Milestone:** M001
**Written:** 2026-04-22T09:55:34.317Z

## S01 UAT

1. `ls meanvc_gui/main_enhanced.py meanvc_gui/main_modern.py 2>&1` → both report "No such file"
2. `ls meanvc_gui/components/enhanced_theme.py meanvc_gui/components/modern_theme.py 2>&1` → both report "No such file"
3. `python -c "from meanvc_gui.core.profile_db import DB_PATH; print(DB_PATH)"` → prints `/path/to/MeanVC/data/meanvc.db` (no `meanvc_gui` in path)
4. `grep -r 'flet\|Flet' meanvc_gui/ --include='*.py'` → zero matches
5. `cat .gitignore | grep '/data/'` → present
