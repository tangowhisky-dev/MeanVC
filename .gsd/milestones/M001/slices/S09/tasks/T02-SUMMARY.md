---
id: T02
parent: S09
milestone: M001
key_files:
  - (none)
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-22T10:33:47.920Z
blocker_discovered: false
---

# T02: README rewritten with accurate asset paths, GUI section, and feature table

**README rewritten with accurate asset paths, GUI section, and feature table**

## What Happened

README rewritten from scratch: corrected asset paths (assets/ckpt/, assets/wavLM/), added desktop app section with feature table and data directory layout, CLI examples, training section preserved, TODO updated with GUI checkbox.

## Verification

grep for stale paths returns zero

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -c 'src/ckpt\|meanvc_gui/data\|src/runtime/speaker_verification/ckpt' README.md` | 1 | ✅ pass — exit 1 means zero matches found | 20ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

None.
