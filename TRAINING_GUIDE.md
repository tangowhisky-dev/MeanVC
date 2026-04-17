# MeanVC Training Guide

## Overview

MeanVC is a lightweight zero-shot voice conversion system using Diffusion Transformer (DiT) with Mean Flow for single-step generation. The model has approximately **14 million parameters**.

---

## 1. Pre-trained Model Weights

### Available Checkpoints

| Model | File | Description | Source |
|-------|------|-------------|--------|
| DiT (200ms) | `model_200ms.safetensors` | Main VC model (safetensors) | HuggingFace |
| DiT (200ms) | `meanvc_200ms.pt` | Main VC model (TorchScript) | HuggingFace |
| Vocoder | `vocos.pt` | Vocos vocoder for waveform synthesis | HuggingFace |
| ASR | `fastu2++.pt` | FastU2++ for content features (BN) | HuggingFace |
| Speaker Verification | `wavlm_large_finetune.pth` | WavLM + ECAPA-TDNN for speaker embeddings | Google Drive |

### Download Command

```bash
python download_ckpt.py
```

This downloads all required assets to the `assets/` folder.

---

## 2. Model Architecture

### DiT Configuration (200ms variant)

```json
{
    "dim": 512,
    "depth": 4,
    "heads": 2,
    "ff_mult": 2,
    "bn_dim": 256,
    "conv_layers": 4,
    "chunk_size": 20,
    "dropout": 0.0,
    "qk_norm": "rms_norm"
}
```

- **Parameters**: ~14M
- **Content conditioning**: Bottleneck features (BN) from FastU2++ ASR
- **Speaker conditioning**: 256-dim xvector from WavLM + ECAPA-TDNN
- **Prompt conditioning**: 2000-frame mel spectrogram

---

## 3. Data Preprocessing Pipeline

### Required Features

Each training sample requires **4 types of features**:

1. **Mel Spectrogram** (80 mel bins, 10ms frame shift)
   - Shape: `(frames, 80)`
   - Used for: target speech, prompt

2. **Bottleneck Features (BN)** (from FastU2++ ASR)
   - Shape: `(frames, 256)`
   - Used for: content conditioning

3. **Speaker Embedding (xvector)**
   - Shape: `(256,)`
   - Used for: speaker conditioning

4. **Prompt Mel** (from reference speaker)
   - Shape: `(2000, 80)`
   - Used for: zero-shot prompting

### Preprocessing Scripts

#### Step 1: Extract Mel Spectrograms

```bash
python src/preprocess/extrace_mel_10ms.py \
    --input_dir path/to/wavs \
    --output_dir path/to/mels \
    --device cuda  # or mps, cpu
```

**Parameters**:
- `sample_rate`: 16000 (default)
- `n_fft`: 1024
- `win_size`: 640 (40ms window)
- `hop_length`: 160 (10ms frame shift)
- `n_mels`: 80

#### Step 2: Extract Bottleneck Features

```bash
# For 200ms model (config_200ms.json)
python src/preprocess/extract_bn_200ms.py \
    --input_dir path/to/wavs \
    --output_dir path/to/bn

# For 160ms model (config_160ms.json)
python src/preprocess/extract_bn_160ms.py \
    --input_dir path/to/wavs \
    --output_dir path/to/bn
```

**Note**: This requires the FastU2++ model (`fastu2++.pt`) loaded from `assets/ckpt/`.

#### Step 3: Extract Speaker Embeddings

```bash
python src/preprocess/extract_spk_emb_wavlm.py \
    --input_dir path/to/wavs \
    --output_dir path/to/xvectors \
    --device cuda  # or mps, cpu
```

**Note**: This requires WavLM checkpoint (`wavlm_large_finetune.pth`) in `assets/wavLM/`.

---

## 4. Training Data Format

### File List Format

Create a text file with one line per sample:

```
<utt_id>|<bn_path>|<mel_path>|<xvector_path>|<prompt_mel_path1>|<prompt_mel_path2>|...
```

**Example**:
```
utt_001|/data/bn/utt_001.npy|/data/mel/utt_001.npy|/data/xvector/utt_001.npy|/data/mel/prompt_001.npy|/data/mel/prompt_002.npy
```

**Required fields**:
- `utt_id`: Unique utterance ID
- `bn_path`: Path to BN feature .npy file
- `mel_path`: Path to mel spectrogram .npy file
- `xvector_path`: Path to speaker embedding .npy file
- `prompt_mel_path*`: At least one prompt mel path (can be same as mel_path for self-prompting)

### Data Requirements

- **Format**: NumPy `.npy` files
- **Mel shape**: `(frames, 80)` - will be truncated to `max_len` (default 1000)
- **BN shape**: `(frames, 256)` - automatically upsampled 4x
- **Xvector shape**: `(256,)` - single vector per utterance
- **Prompt mel**: `(≥2000, 80)` - will be randomly cropped to 2000 frames

---

## 5. Training Command

### Basic Training

```bash
export MEANVC_DEVICE=cuda  # or mps, cpu

bash scripts/train.sh "0"  # Use GPU 0
```

### Key Hyperparameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--epochs` | 1000 | Number of training epochs |
| `--batch-size` | 16 | Batch size per GPU |
| `--learning-rate` | 1e-4 | Initial learning rate |
| `--grad-accumulation-steps` | 1 | Gradient accumulation |
| `--max-grad-norm` | 1.0 | Gradient clipping |
| `--flow-ratio` | 0.50 | Mean Flow ratio in CFM |
| `--cfg-ratio` | 0.1 | Classifier-free guidance ratio |
| `--cfg-scale` | 2.0 | CFG scale |
| `--chunk-size` | 16/20 | Inference chunk size |
| `--num-warmup-updates` | 20000 | Learning rate warmup steps |
| `--save-per-updates` | 10000 | Save checkpoint every N updates |
| `--max-len` | 1000 | Maximum sequence length |

### Training with Custom Dataset

1. Place your audio files in `path/to/wavs/`
2. Run preprocessing (Section 3)
3. Create training list (Section 4)
4. Modify `scripts/train.sh`:
   - Change `--dataset-path` to your list file
   - Change `--exp-name` for your experiment
   - Adjust hyperparameters as needed

---

## 6. Training from Scratch vs Fine-tuning

### Training from Scratch

**When to train from scratch**:
- Completely new dataset with different acoustic characteristics
- Target languages not supported by pre-trained models
- Research on architecture modifications

**Recommended setup**:
- **Data**: Minimum 100+ hours of clean speech
- **Epochs**: 500-1000
- **Learning rate**: 1e-4 (with warmup)
- **Batch size**: 16 per GPU (scale with GPUs)
- **Checkpointing**: Save every 10k steps
- **Training time**: ~1-2 weeks on 8 GPUs

**Example**:
```bash
accelerate launch --config-file default_config.yaml \
    --num_processes 8 \
    src/train/train.py \
    --model-config src/config/config_160ms.json \
    --batch-size 16 \
    --epochs 1000 \
    --learning-rate 1e-4 \
    --num-warmup-updates 20000 \
    --dataset-path your_train.list \
    --exp-name scratch_training
```

### Fine-tuning Pre-trained Model

**When to fine-tune**:
- Adding support for new languages (Urdu, Hindi, Pashto, etc.)
- Improving quality for specific speaker accents
- Domain adaptation (different recording conditions)

**Recommended setup**:
- **Data**: Minimum 10-50 hours of clean speech
- **Epochs**: 50-200
- **Learning rate**: Lower than scratch (1e-5 to 5e-5)
- **Reset LR**: `--reset-lr 1` to restart learning rate schedule
- **Checkpointing**: Save every 5k steps

**Example**:
```bash
# Fine-tune with lower learning rate
accelerate launch --config-file default_config.yaml \
    --num_processes 4 \
    src/train/train.py \
    --model-config src/config/config_200ms.json \
    --batch-size 8 \
    --epochs 100 \
    --learning-rate 5e-5 \
    --reset-lr 1 \
    --num-warmup-updates 1000 \
    --pretrained-ckpt-path assets/ckpt/model_200ms.safetensors \
    --dataset-path your_train.list \
    --exp-name finetune_urdu
```

---

## 7. Mozilla Common Voice for Local Languages

### Available Datasets (2025-2026)

| Language | Code | Total Hours | Validated Hours | Speakers | Version |
|----------|------|-------------|-----------------|----------|---------|
| Urdu | `ur` | ~302 | ~81 | ~500 | CV24 |
| Pashto | `ps` | ~2769 | ~976 | ~6654 | CV24 |
| Punjabi | `pa` | ~200+ | ~70+ | ~1000+ | CV23+ |
| Hindi | `hi` | ~500+ | ~150+ | ~2000+ | CV24 |
| Balti | `bs` | Limited | Limited | Limited | CV15 |

### Data Download

1. Visit [Mozilla Common Voice](https://commonvoice.mozilla.org/)
2. Select your target language
3. Download the dataset (CC0 licensed)
4. Extract audio files (.mp3, .wav)

### Processing for Voice Conversion

For voice conversion, you need **speaker-diverse data**:

1. **Minimum data for fine-tuning**:
   - 10+ hours for basic fine-tuning
   - 50+ hours for high-quality results

2. **Preprocessing steps**:
   - Convert MP3 to WAV (16kHz mono)
   - Filter out noisy recordings (use validated splits)
   - Ensure diverse speakers (>50 speakers recommended)

3. **Data splitting**:
   - Train: 80-90% of validated clips
   - Validation: 5-10%
   - Test: 5-10%

### Language-Specific Notes

**Urdu (اردو)**:
- ~80 validated hours available
- Good for South Asian accent adaptation
- Consider mixing with Hindi for larger dataset

**Pashto (پښتو)**:
- ~976 validated hours (large dataset!)
- Good for Pashto-specific fine-tuning
- Diverse speaker base (~6.6k speakers)

**Punjabi (ਪੰਜਾਬੀ)**:
- ~70+ validated hours
- Consider mixing with Hindi/Urdu for better coverage

**Hindi (हिन्दी)**:
- ~150+ validated hours
- Large speaker diversity
- Best resourced among South Asian languages

### Recommended Fine-tuning Strategy for Low-Resource Languages

#### Phase 1: Data Preparation (Priority)
1. **Combine multiple languages**: Merge Urdu + Hindi + Pashto for larger training set
2. **Speaker diversity**: Ensure 50+ speakers minimum
3. **Audio quality**: Filter to validated clips only
4. **Duration**: Aim for 20+ hours minimum

#### Phase 2: Training Configuration
```
# Recommended fine-tuning parameters
--epochs 50-100           # Fewer epochs for fine-tuning
--learning-rate 5e-5      # Lower than scratch
--reset-lr 1              # Fresh LR schedule
--batch-size 8-16         # Smaller batch for fine-tuning
--num-warmup-updates 500  # Shorter warmup
--save-per-updates 5000   # More frequent saves
```

#### Phase 3: Evaluation
- Use WER (Word Error Rate) from ASR model for evaluation
- Calculate speaker similarity (SSMI) for voice quality
- Test on held-out speakers not seen during training

### Data Quality Guidelines

| Aspect | Requirement |
|--------|-------------|
| Audio format | 16kHz, mono WAV preferred |
| Clip duration | 3-20 seconds |
| Noise level | Low (validated clips only) |
| Speaker balance | < 10% from single speaker |
| Transcript accuracy | Required for content features |

---

## 8. Device Configuration

MeanVC supports CUDA, MPS (Apple Silicon), and CPU:

```bash
# Via environment variable (recommended)
export MEANVC_DEVICE=cuda   # NVIDIA GPU
export MEANVC_DEVICE=mps    # Apple Silicon
export MEANVC_DEVICE=cpu    # CPU only

# Via command line
python src/train/train.py --device mps ...
```

### Training on Apple Silicon (MPS)

- Use `--device mps` or `export MEANVC_DEVICE=mps`
- Single GPU only (no DDP)
- AMP disabled automatically
- Set `num_workers=0` in training args

---

## 9. Troubleshooting

| Issue | Solution |
|-------|----------|
| Training stuck at 0% | Set `num_workers=0` for MPS; check dataloader |
| Out of memory | Reduce `batch-size` or `max-len` |
| Slow training on MPS | Use smaller model (160ms variant) |
| No improvement in fine-tuning | Try lower learning rate (1e-5) |
| Checkpoint loading errors | Use `--reset-lr 1` for fresh training |

---

## 10. Summary Checklist

- [ ] Download pre-trained weights: `python download_ckpt.py`
- [ ] Prepare audio data (16kHz mono recommended)
- [ ] Run preprocessing: mel → BN → xvector
- [ ] Create training list with correct format
- [ ] Choose training mode: scratch or fine-tune
- [ ] Set device: `export MEANVC_DEVICE=cuda` (or mps/cpu)
- [ ] Start training: `bash scripts/train.sh "0"`
- [ ] Monitor with Weights & Biases (optional)
- [ ] Evaluate with validation set periodically