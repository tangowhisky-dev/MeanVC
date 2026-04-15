import soundfile as sf
import torch
import os
from collections import defaultdict
import argparse
from tqdm import tqdm
import numpy as np
import torch.nn.functional as F
from torchaudio.transforms import Resample
from .ecapa_tdnn import ECAPA_TDNN_SMALL
import glob
from src.utils.audio import get_device

# All supported self-supervised speech models (HuggingFace transformers)
MODEL_LIST = [
    "ecapa_tdnn",
    "hubert_large",
    "wav2vec2_xlsr",
    "unispeech_sat",
    "wavlm_base_plus",
    "wavlm_large",
]


def init_model(model_name, checkpoint=None, num_class: int = 0):
    """Initialise an ECAPA-TDNN speaker verification model.

    Parameters
    ----------
    model_name : str
        One of ``'wavlm_large'``, ``'wavlm_base_plus'``, ``'hubert_large'``,
        ``'wav2vec2_xlsr'``, ``'unispeech_sat'``, or ``'ecapa_tdnn'`` (fbank).
    checkpoint : str, optional
        Path to a fine-tuned ECAPA-TDNN checkpoint (``.pth``). The checkpoint
        should contain a ``'model'`` key with the state dict.
    num_class : int, optional
        Number of speaker classes for the AAM-softmax loss head.  Required
        when training from scratch or resuming training.  Pass 0 (default)
        for inference-only — the ``loss_calculator`` submodule is omitted.
        When loading wavlm_large_finetune.pth for training, pass 5994 to
        restore the full trained loss head.

    Returns
    -------
    ECAPA_TDNN
    """
    if model_name == "unispeech_sat":
        model = ECAPA_TDNN_SMALL(
            feat_dim=1024, feat_type="unispeech_sat", num_class=num_class
        )
    elif model_name == "wavlm_base_plus":
        model = ECAPA_TDNN_SMALL(
            feat_dim=768, feat_type="wavlm_base_plus", num_class=num_class
        )
    elif model_name == "wavlm_large":
        model = ECAPA_TDNN_SMALL(
            feat_dim=1024, feat_type="wavlm_large", num_class=num_class
        )
    elif model_name == "hubert_large":
        model = ECAPA_TDNN_SMALL(
            feat_dim=1024, feat_type="hubert_large_ll60k", num_class=num_class
        )
    elif model_name == "wav2vec2_xlsr":
        model = ECAPA_TDNN_SMALL(
            feat_dim=1024, feat_type="wav2vec2_xlsr", num_class=num_class
        )
    else:
        model = ECAPA_TDNN_SMALL(feat_dim=40, feat_type="fbank", num_class=num_class)

    if checkpoint is not None:
        state_dict = torch.load(checkpoint, map_location="cpu", weights_only=True)
        raw = state_dict["model"]
        # Remap s3prl key prefix: feature_extract.model.* → feature_extract.wavlm.*
        remapped = {
            k.replace("feature_extract.model.", "feature_extract.wavlm."): v
            for k, v in raw.items()
        }
        result = model.load_state_dict(remapped, strict=False)
        # Unexpected: loss_calculator present in ckpt but model built with num_class=0
        # Missing: loss_calculator absent in ckpt but model built with num_class>0
        # Both are surfaced as warnings so callers can catch misconfiguration.
        unexpected = [k for k in result.unexpected_keys if "loss_calculator" not in k]
        missing = [k for k in result.missing_keys]
        if unexpected:
            print(f"  [SV] unexpected keys: {unexpected[:5]}")
        if missing:
            print(f"  [SV] missing keys: {missing[:5]}")
    return model


def get_emb(model, wav, device="cpu", sample_rate=16000):
    wav, sr = sf.read(wav)
    if wav.ndim == 2:
        wav = np.mean(wav, axis=1)

    wav = torch.from_numpy(wav).unsqueeze(0).float().to(device)

    if sr != sample_rate:
        resample = Resample(orig_freq=sr, new_freq=sample_rate).to(device)
        wav = resample(wav)

    with torch.no_grad():
        emb = model(wav)

    return emb


def verification_v1(model, target_spk, wavs, device="cpu", sample_rate=16000):
    target_spk_emb = get_emb(model, target_spk, device, sample_rate)
    spk_sims = {}
    for wav in tqdm(wavs):
        emb = get_emb(model, wav, device, sample_rate)
        spk_sims[wav] = F.cosine_similarity(target_spk_emb, emb)
    return spk_sims


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wavs")
    parser.add_argument("--target_spk")
    parser.add_argument("--output")
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()

    wav_dir = args.wavs
    target_spk = args.target_spk
    output = args.output
    device = args.device

    wavs = glob.glob(os.path.join(wav_dir, "*.wav"))

    # Resolve checkpoint path relative to project root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    ckpt_path = os.path.join(
        project_root, "assets", "wavLM", "wavlm_large_finetune.pth"
    )

    model = init_model("wavlm_large", ckpt_path)
    model.eval()
    model.to(device)

    sims = verification_v1(model, target_spk, wavs, device, 16000)
    with open(output, "w") as f:
        f.write(f"{sum(sims.values()) / len(list(sims.keys()))}\n")
        for key, value in sims.items():
            f.write(f"{key}: {value}\n")
