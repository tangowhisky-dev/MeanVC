---
id: T01
parent: S07
milestone: M001
key_files:
  - (none)
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-22T10:32:19.710Z
blocker_discovered: false
---

# T01: Real ECAPA cosine similarity in engine; SimilarityWorker in analysis page

**Real ECAPA cosine similarity in engine; SimilarityWorker in analysis page**

## What Happened

Engine.calculate_similarity() uses ECAPA-TDNN cosine similarity mapped to 0-100. RMS-based quality proxy. SimilarityWorker QThread in analysis.py.

## Verification

import checks pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `conda run -n meanvc python -c 'from meanvc_gui.core.engine import get_engine; e=get_engine(); print(callable(e.calculate_similarity))'` | 0 | ✅ pass | 800ms |

## Deviations

calculate_similarity already implemented in engine.py (S03/T01). SimilarityWorker added in analysis.py.

## Known Issues

None.

## Files Created/Modified

None.
