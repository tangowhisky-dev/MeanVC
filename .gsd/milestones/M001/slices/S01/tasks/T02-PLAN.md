---
estimated_steps: 7
estimated_files: 2
skills_used: []
---

# T02: Move DB to root data/ and fix profile_db.py

1. Read meanvc_gui/core/profile_db.py.
2. PROJECT_ROOT is currently dirname(dirname(abspath(__file__))) which resolves to repo root — this is already correct for data/ at repo root.
3. Verify DATA_DIR resolves to <repo_root>/data/ not <repo_root>/meanvc_gui/data/.
4. If meanvc_gui/data/meanvc.db exists, delete it (it's empty/dev only).
5. Ensure data/ is in .gitignore.
6. Add data/profiles/ to .gitignore.
7. Run python -c 'from meanvc_gui.core.profile_db import DB_PATH; print(DB_PATH)' and confirm path ends with /data/meanvc.db (not meanvc_gui/data/).

## Inputs

- `meanvc_gui/core/profile_db.py`
- `.gitignore`

## Expected Output

- `DB_PATH ends with /data/meanvc.db (no meanvc_gui in path)`
- `data/ in .gitignore`

## Verification

python -c "import sys; sys.path.insert(0,''); from meanvc_gui.core.profile_db import DB_PATH; assert 'meanvc_gui' not in DB_PATH, f'Wrong path: {DB_PATH}'; print('DB path OK:', DB_PATH)"
