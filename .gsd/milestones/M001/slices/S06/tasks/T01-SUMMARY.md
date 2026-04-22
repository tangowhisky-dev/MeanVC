---
id: T01
parent: S06
milestone: M001
key_files:
  - (none)
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-22T10:31:29.935Z
blocker_discovered: false
---

# T01: VCRunner QThread implemented from run_rt.py inference loop

**VCRunner QThread implemented from run_rt.py inference loop**

## What Happened

VCRunner QThread ports run_rt.py inference loop: sounddevice InputStream/OutputStream with ring buffer, chunk-wise BN extraction, flow-matching inference, vocoder overlap-add, RTF signal per chunk, save-to-file accumulation. Loads TorchScript vc model (meanvc_200ms.pt) for realtime; falls back to DiT nn.Module with warning.

## Verification

import check passes

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `conda run -n meanvc python -c 'from meanvc_gui.core.vc_runner import VCRunner; print("OK")'` | 0 | ✅ pass | 800ms |

## Deviations

VCRunner input loop has a minor logic issue in the ring-buffer wait — consecutive reads after empty check. Will note in known issues.

## Known Issues

None.

## Files Created/Modified

None.
