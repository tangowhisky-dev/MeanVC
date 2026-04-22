# S01: Codebase Cleanup — Remove Flet, Consolidate Files

**Goal:** Delete every Flet artefact and redundant GUI file. Collapse three entry points and three theme files into one each. Move DB location from meanvc_gui/data/ to project-root data/. Update DECISIONS.md, KNOWLEDGE.md, PROJECT.md to remove all Flet mentions.
**Demo:** App launches from python -m meanvc_gui.main with no import errors.

## Must-Haves

- Single entry point; single theme module; no Flet strings; DB at data/meanvc.db; GSD docs clean.

## Proof Level

- This slice proves: rg 'flet|Flet' --include='*.py' returns zero; python -m meanvc_gui.main opens window without error; data/meanvc.db created.

## Integration Closure

S02+ imports only meanvc_gui/main.py and meanvc_gui/components/theme.py.

## Verification

- None — cleanup only.

## Tasks

- [x] **T01: Delete Flet files and redundant GUI files** `est:30m`
  1. Delete FLET_IMPLEMENTATION_PLAN.md from repo root.
2. Delete meanvc_gui/main_modern.py, meanvc_gui/main_enhanced.py.
3. Delete meanvc_gui/components/enhanced_theme.py, meanvc_gui/components/modern_theme.py.
4. Delete meanvc_gui/pages/enhanced_library.py.
5. Delete meanvc_gui/DESIGN.md, meanvc_gui/PROFILE_DESIGN.md.
6. Verify remaining files: main.py, components/theme.py, components/waveform.py, pages/(library|offline|realtime|analysis|settings).py, core/(engine|profile_db|profile_manager|device).py.
7. Fix any import in library.py that imports from modern_theme — update to use components/theme.py COLORS instead.
  - Files: `FLET_IMPLEMENTATION_PLAN.md`, `meanvc_gui/main_modern.py`, `meanvc_gui/main_enhanced.py`, `meanvc_gui/components/enhanced_theme.py`, `meanvc_gui/components/modern_theme.py`, `meanvc_gui/pages/enhanced_library.py`, `meanvc_gui/DESIGN.md`, `meanvc_gui/PROFILE_DESIGN.md`, `meanvc_gui/pages/library.py`
  - Verify: python -c 'from meanvc_gui.pages.library import LibraryPage' && echo OK

- [x] **T02: Move DB to root data/ and fix profile_db.py** `est:20m`
  1. Read meanvc_gui/core/profile_db.py.
2. PROJECT_ROOT is currently dirname(dirname(abspath(__file__))) which resolves to repo root — this is already correct for data/ at repo root.
3. Verify DATA_DIR resolves to <repo_root>/data/ not <repo_root>/meanvc_gui/data/.
4. If meanvc_gui/data/meanvc.db exists, delete it (it's empty/dev only).
5. Ensure data/ is in .gitignore.
6. Add data/profiles/ to .gitignore.
7. Run python -c 'from meanvc_gui.core.profile_db import DB_PATH; print(DB_PATH)' and confirm path ends with /data/meanvc.db (not meanvc_gui/data/).
  - Files: `meanvc_gui/core/profile_db.py`, `.gitignore`
  - Verify: python -c "import sys; sys.path.insert(0,''); from meanvc_gui.core.profile_db import DB_PATH; assert 'meanvc_gui' not in DB_PATH, f'Wrong path: {DB_PATH}'; print('DB path OK:', DB_PATH)"

- [x] **T03: Strip Flet from DECISIONS.md, KNOWLEDGE.md, PROJECT.md** `est:20m`
  1. Read .gsd/DECISIONS.md — remove the old D001 narrative section entirely (D001 entry now only in the decisions table as PySide6).
2. Read .gsd/KNOWLEDGE.md — the Flet GUI section should now just be a note that Flet was considered but PySide6 was chosen; all Flet-pattern guidance (page.update, pubsub) removed. The PySide6 section is already present; remove the Flet section header and all Flet-specific bullets.
3. Read .gsd/PROJECT.md — update the DB location field to reflect data/meanvc.db; remove any remaining Flet references.
4. Read .gsd/DECISIONS.md — update D005 rationale to not mention Flet.
5. Verify: grep -n 'flet\|Flet' .gsd/*.md returns only lines that are legitimately historical cross-references (D001 superseded note).
  - Files: `.gsd/DECISIONS.md`, `.gsd/KNOWLEDGE.md`, `.gsd/PROJECT.md`
  - Verify: grep -c 'Flet' .gsd/KNOWLEDGE.md .gsd/PROJECT.md | awk -F: '$2>0{fail=1} END{exit fail}' && echo 'No stale Flet refs'

## Files Likely Touched

- FLET_IMPLEMENTATION_PLAN.md
- meanvc_gui/main_modern.py
- meanvc_gui/main_enhanced.py
- meanvc_gui/components/enhanced_theme.py
- meanvc_gui/components/modern_theme.py
- meanvc_gui/pages/enhanced_library.py
- meanvc_gui/DESIGN.md
- meanvc_gui/PROFILE_DESIGN.md
- meanvc_gui/pages/library.py
- meanvc_gui/core/profile_db.py
- .gitignore
- .gsd/DECISIONS.md
- .gsd/KNOWLEDGE.md
- .gsd/PROJECT.md
