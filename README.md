# MeanVC: Lightweight and Streaming Zero-Shot Voice Conversion via Mean Flows

<div align="center">

[![Paper](https://img.shields.io/badge/arXiv-2510.08392-b31b1b.svg)](https://arxiv.org/pdf/2510.08392)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Models-yellow)](https://huggingface.co/ASLP-lab/MeanVC)
[![Demo Page](https://img.shields.io/badge/Demo-Audio%20Samples-green)](https://aslp-lab.github.io/MeanVC/)

</div>

**MeanVC** is a lightweight and streaming zero-shot voice conversion system that enables real-time timbre transfer from any source speaker to any target speaker while preserving linguistic content. The system introduces a diffusion transformer with chunk-wise autoregressive denoising strategy and mean flows for efficient single-step inference.

![img](figs/model.png)

## ✨ Key Features

- **🚀 Streaming Inference** — Real-time voice conversion with chunk-wise processing (200ms latency).
- **⚡ Single-Step Generation** — Direct mapping via mean flows; 1–2 denoising steps suffice.
- **🎯 Zero-Shot** — Convert to any unseen target speaker; no fine-tuning or training required.
- **💾 Lightweight** — Significantly fewer parameters than existing methods.
- **🖥 Desktop App** — Full PySide6 GUI with profile library, offline batch, realtime, and analysis pages.

---

## 🚀 Getting Started

### 1. Environment Setup

```bash
# Conda (recommended)
conda create -n meanvc python=3.11 -y
conda activate meanvc
pip install -r requirements.txt

# OR uv venv
uv venv ~/.meanvc --python 3.11
source ~/.meanvc/bin/activate
pip install -r requirements.txt
```

### 2. Download Pre-trained Models

```bash
python download_ckpt.py
```

This downloads the following files into `assets/`:

| File | Destination | Notes |
|------|-------------|-------|
| `model_200ms.safetensors` | `assets/ckpt/` | DiT checkpoint |
| `meanvc_200ms.pt` | `assets/ckpt/` | DiT TorchScript (realtime) |
| `vocos.pt` | `assets/ckpt/` | Vocos vocoder TorchScript |
| `fastu2++.pt` | `assets/ckpt/` | FastU2++ ASR TorchScript |

**WavLM speaker model (manual download required):**

Download [`wavlm_large_finetune.pth`](https://drive.google.com/file/d/1-aE1NfzpRCLxA4GUxX9ITI3F9LlbtEGP/view) from Google Drive and place it at:
```
assets/wavLM/wavlm_large_finetune.pth
```

### 3. Device Selection

MeanVC auto-selects `CUDA → MPS → CPU`. Override with:

```bash
export MEANVC_DEVICE=cuda   # or mps / cpu / cuda:1
```

---

## 🖥 Desktop App (PySide6)

### Install GUI dependencies

```bash
pip install -r meanvc_gui/requirements.txt
```

### Launch

```bash
python -m meanvc_gui.main
```

### Features

| Page | Description |
|------|-------------|
| **Library** | Create voice profiles; upload reference audio; WavLM embedding extraction; export/import profile zip |
| **Offline** | File-based conversion with profile picker, steps slider, output directory, progress bar, playback |
| **Realtime** | Live microphone conversion; profile/device picker; RTF display; optional output recording |
| **Analysis** | Speaker similarity score (ECAPA-TDNN cosine); quality metrics; bar chart visualisation |
| **Settings** | Real asset status from disk; one-click download of missing assets; device override |

### Data directory

All profile audio and embeddings are stored in `data/` at the project root (gitignored):
```
data/
  meanvc.db          ← SQLite profile database
  profiles/
    <profile_id>/
      audio/         ← reference WAV files
      embeddings/    ← WavLM .pt embedding files
      prompt/        ← mel spectrogram .npy files
```

---

## 💻 CLI Usage

### Real-time conversion

```bash
python src/runtime/run_rt.py --target-path "path/to/reference.wav"
```

### Offline batch conversion

```bash
python convert.py \
  --source path/to/source.wav \
  --reference path/to/reference.wav \
  --output path/to/output_dir/ \
  --steps 2
```

Or use the convenience script:

```bash
# Edit paths in scripts/infer_ref.sh first
bash scripts/infer_ref.sh
```

---

## 🏋️‍♀️ Training

### 1. Data Preprocessing

```bash
export MEANVC_DEVICE=cuda

# Extract mel spectrograms (10ms hop)
python src/preprocess/extrace_mel_10ms.py \
  --input_dir path/to/wavs --output_dir path/to/mels

# Extract BN content features (200ms)
python src/preprocess/extract_bn_200ms.py \
  --input_dir path/to/wavs --output_dir path/to/bns

# Extract speaker embeddings
python src/preprocess/extract_spk_emb_wavlm.py \
  --input_dir path/to/wavs --output_dir path/to/xvectors
```

### 2. Prepare Data List

```
# Format: utt|bn_path|mel_path|xvector_path|prompt_mel_path
utt001|/path/bns/utt001.npy|/path/mels/utt001.npy|/path/xvectors/utt001.npy|/path/mels/prompt01.npy
```

### 3. Train

```bash
bash scripts/train.sh
```

---

## 📋 TODO

- [x] 🌐 Demo website
- [x] 📝 Paper release
- [x] 🤗 HuggingFace model release
- [x] 🔓 Inference code
- [x] 🔓 Training code
- [x] 🖥 Desktop GUI (PySide6)
- [ ] 📱 Android deployment package

---

## 📜 License & Disclaimer

MeanVC is released under the Apache License 2.0. Users must obtain proper consent from individuals whose voices are used as references. The authors strongly discourage any malicious use including impersonation, fraud, or misleading audio content. Users are solely responsible for compliance with ethical and legal requirements.

## ❤️ Acknowledgments

Built upon [MeanFlow](https://github.com/haidog-yaqub/MeanFlow), [F5-TTS](https://github.com/SWivid/F5-TTS), and [Vocos](https://github.com/gemelo-ai/vocos).

## 📄 Citation

```bibtex
@article{ma2025meanvc,
  title={MeanVC: Lightweight and Streaming Zero-Shot Voice Conversion via Mean Flows},
  author={Ma, Guobin and Yao, Jixun and Ning, Ziqian and Jiang, Yuepeng and Xiong, Lingxin and Xie, Lei and Zhu, Pengcheng},
  journal={arXiv preprint arXiv:2510.08392},
  year={2025}
}
```

## 📧 Contact

guobin.ma@mail.nwpu.edu.cn

<p align="center">
    <img src="figs/meanvc_QR.png" width="300"/>
</p>

<p align="center">
    <img src="figs/npu@aslp.jpeg" height="120" style="margin-right: 20px;"/>
    <img src="figs/geely_logo.jpg" height="120"/>
</p>
