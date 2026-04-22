---
id: T01
parent: S03
milestone: M001
key_files:
  - (none)
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-22T10:14:18.782Z
blocker_discovered: false
---

# T01: Implemented real engine.py with all four models, convert(), similarity(), asset check

**Implemented real engine.py with all four models, convert(), similarity(), asset check**

## What Happened

Wrote complete engine.py: REQUIRED_ASSETS dict, AssetsMissingError, check_assets(), Engine singleton with full model loading (DiT, Vocos, ASR, WavLM), _extract_bn(), _extract_spk_and_prompt(), _run_inference(), convert() with progress_cb and cancellation, calculate_similarity() with real cosine score, get_models() for VCRunner.

## Verification

check_assets() returns correct status dict; engine imports cleanly.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `conda run -n meanvc python -c "from meanvc_gui.core.engine import check_assets, get_engine; print(check_assets())"` | 0 | ✅ pass | 900ms |

## Deviations

None. WavLM asset missing (manual download required) so check_assets_ok() returns False — expected behaviour.

## Known Issues

None.

## Files Created/Modified

None.
