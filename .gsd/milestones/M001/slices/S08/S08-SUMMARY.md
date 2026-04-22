---
id: S08
parent: M001
milestone: M001
provides:
  - (none)
requires:
  []
affects:
  []
key_files:
  - (none)
key_decisions:
  - (none)
patterns_established:
  - (none)
observability_surfaces:
  - none
drill_down_paths:
  []
duration: ""
verification_result: passed
completed_at: 2026-04-22T10:33:11.078Z
blocker_discovered: false
---

# S08: Settings Page — Real Asset Check + Download

**Settings page complete with real asset check and live download progress**

## What Happened

Settings page shows real ✓/✗ asset status with file sizes. DownloadWorker runs download_ckpt.py in subprocess streaming output line-by-line to log. Device combo applies to os.environ.

## Verification

Import check passes; check_assets() returns correct status dict.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Operational Readiness

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `meanvc_gui/pages/settings.py` — Complete rewrite: real asset status, DownloadWorker subprocess, log textarea, device override
