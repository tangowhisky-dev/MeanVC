---
id: T03
parent: S03
milestone: M001
key_files:
  - (none)
key_decisions:
  - (none)
duration: 
verification_result: passed
completed_at: 2026-04-22T10:14:54.986Z
blocker_discovered: false
---

# T03: Fixed WavLM path and mel extractor in profile_manager.py; added EmbeddingWorker, export/import

**Fixed WavLM path and mel extractor in profile_manager.py; added EmbeddingWorker, export/import**

## What Happened

Fixed extract_wavlm_embedding to use init_sv_model('wavlm_large', path) with correct asset path at assets/wavLM/wavlm_large_finetune.pth. Added 10s SV cap. Fixed extract_mel_spectrogram to use MelSpectrogramFeatures with matching parameters. Removed aiofiles import. Added EmbeddingWorker QThread. Added export_profile() and import_profile().

## Verification

EmbeddingWorker class importable; mel extractor uses MelSpectrogramFeatures not torchaudio.transforms.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `conda run -n meanvc python -c 'from meanvc_gui.core.profile_manager import EmbeddingWorker, extract_mel_spectrogram; print("T03 OK")'` | 0 | ✅ pass | 900ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

None.
