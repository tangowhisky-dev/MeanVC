---
id: T02
parent: S01
milestone: M001
key_files:
  - (none)
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-22T09:55:08.720Z
blocker_discovered: false
---

# T02: Fixed DB path to resolve to project-root data/meanvc.db; removed old meanvc_gui/data/; updated .gitignore

**Fixed DB path to resolve to project-root data/meanvc.db; removed old meanvc_gui/data/; updated .gitignore**

## What Happened

profile_db.py PROJECT_ROOT used dirname×2 yielding meanvc_gui/ instead of repo root. Added a third dirname(). Removed meanvc_gui/data/ dir. Added /data/ to .gitignore.

## Verification

python -c confirms DB_PATH=/Users/tango16/code/MeanVC/data/meanvc.db

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "from meanvc_gui.core.profile_db import DB_PATH; assert 'meanvc_gui' not in DB_PATH; print(DB_PATH)"` | 0 | ✅ pass | 200ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

None.
