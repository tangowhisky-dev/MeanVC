# Codebase Map

Generated: 2026-04-15T21:57:59Z | Files: 76 | Described: 0/76
<!-- gsd:codebase-meta {"generatedAt":"2026-04-15T21:57:59Z","fingerprint":"d1dc61f76766892e0cdbbf10ffaa02c8fa5f0792","fileCount":76,"truncated":false} -->

### (root)/
- `.DS_Store`
- `.gitignore`
- `convert.py`
- `default_config.yaml`
- `defaults.ini`
- `download_ckpt.py`
- `LICENSE`
- `MPS_COMPATIBILITY_ANALYSIS.md`
- `README.md`
- `requirements.txt`

### meanvc_out/
- `meanvc_out/anchor_converted.wav`

### scripts/
- `scripts/infer_ref.sh`
- `scripts/infer.sh`
- `scripts/train_dis.sh`
- `scripts/train.sh`

### src/
- `src/.DS_Store`

### src/config/
- `src/config/config_160ms.json`
- `src/config/config_200ms.json`

### src/dataset/
- `src/dataset/dataset.py`

### src/eval/
- `src/eval/ecapa_tdnn.py`
- `src/eval/run_wer.py`
- `src/eval/utils.py`
- `src/eval/verification.py`

### src/infer/
- `src/infer/dit_kvcache.py`
- `src/infer/infer_ref.py`
- `src/infer/infer.py`
- `src/infer/modules.py`

### src/model/
- `src/model/__init__.py`
- `src/model/cfm_mean_flow.py`
- `src/model/dit_discriminator.py`
- `src/model/loss.py`
- `src/model/modules.py`
- `src/model/prompt_vp.py`
- `src/model/trainer_dis.py`
- `src/model/trainer.py`
- `src/model/utils.py`

### src/model/backbones/
- `src/model/backbones/dit.py`

### src/preprocess/
- `src/preprocess/extrace_mel_10ms.py`
- `src/preprocess/extract_bn_160ms.py`
- `src/preprocess/extract_bn_200ms.py`
- `src/preprocess/extract_spk_emb_wavlm.py`

### src/preprocess/models/
- `src/preprocess/models/__init__.py`
- `src/preprocess/models/ecapa_tdnn.py`
- `src/preprocess/models/utils.py`

### src/runtime/
- `src/runtime/.DS_Store`
- `src/runtime/run_rt.py`

### src/runtime/example/
- `src/runtime/example/test.wav`

### src/runtime/speaker_verification/
- `src/runtime/speaker_verification/.DS_Store`
- `src/runtime/speaker_verification/ecapa_tdnn.py`
- `src/runtime/speaker_verification/utils.py`
- `src/runtime/speaker_verification/verification.py`

### src/train/
- `src/train/train_2.py`
- `src/train/train.py`

### src/utils/
- `src/utils/__init__.py`
- `src/utils/audio.py`

### src/wavLM/
- `src/wavLM/modules.py`
- `src/wavLM/WavLM.py`

### test_data/
- `test_data/train.list`

### test_data/bn/
- `test_data/bn/test.npy`

### test_data/mel/
- `test_data/mel/test.npy`

### test_data/xvector/
- `test_data/xvector/test.npy`

### tests/
- `tests/simple_train_test.py`
- `tests/test1.py`
- `tests/train_test.py`

### vocos/
- `vocos/__init__.py`
- `vocos/dataset.py`
- `vocos/discriminators.py`
- `vocos/experiment.py`
- `vocos/feature_extractors.py`
- `vocos/heads.py`
- `vocos/helpers.py`
- `vocos/loss.py`
- `vocos/models.py`
- `vocos/modules.py`
- `vocos/pretrained.py`
- `vocos/spectral_ops.py`
