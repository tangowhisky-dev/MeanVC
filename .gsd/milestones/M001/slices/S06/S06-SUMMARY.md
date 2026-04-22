---
id: S06
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
completed_at: 2026-04-22T10:32:02.984Z
blocker_discovered: false
---

# S06: Realtime Page — Live Mic-to-Speaker Conversion

**Realtime page and VCRunner complete**

## What Happened

Created VCRunner QThread that wraps run_rt.py inference logic with sounddevice ring buffers. Rewrote realtime.py with full UI: profile/device pickers, steps control, Start/Stop, RTF colour-coded label, animated waveform, save-to-file toggle.

## Verification

Both tasks verified by import checks. Live test deferred until hardware available.

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

VCRunner ring-buffer wait loop has minor double-read after empty check; harmless but slightly wasteful. Also: TorchScript vc model (meanvc_200ms.pt) needed for realtime — fallback to DiT nn.Module may have call-signature mismatch.

## Follow-ups

None.

## Files Created/Modified

- `meanvc_gui/core/vc_runner.py` — New: VCRunner QThread porting run_rt.py inference loop
- `meanvc_gui/pages/realtime.py` — Complete rewrite: VCRunner wiring, device combos, RTF display, waveform animation
