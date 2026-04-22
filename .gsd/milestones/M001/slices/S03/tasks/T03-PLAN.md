---
estimated_steps: 9
estimated_files: 1
skills_used: []
---

# T03: Fix profile_manager.py WavLM path and mel extractor

1. Fix extract_wavlm_embedding() in profile_manager.py:
   - Remove the wrong WavLM(cfg_path=..., ckpt_path=...) call.
   - Use init_sv_model('wavlm_large', sv_ckpt_path) from src/runtime/speaker_verification/verification.py.
   - sv_ckpt_path = os.path.join(PROJECT_ROOT, 'assets', 'wavLM', 'wavlm_large_finetune.pth').
   - Cap input audio at SV_MAX_SECS=10 before running.
   - Output embedding shape must be [1, 256].
2. Fix extract_mel_spectrogram() to use MelSpectrogramFeatures from src/utils/audio.py instead of torchaudio.transforms.MelSpectrogram (different filterbank!).
3. Remove unused aiofiles import.
4. Add logging for embedding extraction (duration, shape).

## Inputs

- `meanvc_gui/core/profile_manager.py`
- `src/runtime/speaker_verification/verification.py`
- `src/utils/audio.py`

## Expected Output

- `profile_manager.extract_wavlm_embedding writes a [1,256] tensor to .pt file`

## Verification

python -c "
import sys, os, tempfile; sys.path.insert(0,'')
from meanvc_gui.core.profile_manager import extract_wavlm_embedding, extract_mel_spectrogram
with tempfile.TemporaryDirectory() as d:
    emb_ok = extract_wavlm_embedding('src/runtime/example/test.wav', os.path.join(d,'emb.pt'), device='cpu')
    print('embedding extracted:', emb_ok)
"
