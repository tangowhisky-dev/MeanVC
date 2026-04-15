"""Extract speaker embeddings from WAV files using a fine-tuned ECAPA-TDNN model."""

import soundfile as sf
import torch
import os
from collections import defaultdict
import argparse
from tqdm import tqdm
import torch.nn.functional as F
from torchaudio.transforms import Resample
from models.ecapa_tdnn import ECAPA_TDNN_SMALL
import glob
import numpy as np
from functools import partial
from multiprocessing import Pool
import multiprocessing

multiprocessing.set_start_method("spawn", force=True)
from src.utils.audio import get_device

MODEL_LIST = ["wavlm_large"]


def init_model(model_name, checkpoint=None):
    """Initialise an ECAPA-TDNN speaker verification model."""
    if model_name == "unispeech_sat":
        model = ECAPA_TDNN_SMALL(feat_dim=1024, feat_type="unispeech_sat")
    elif model_name == "wavlm_base_plus":
        model = ECAPA_TDNN_SMALL(feat_dim=768, feat_type="wavlm_base_plus")
    elif model_name == "wavlm_large":
        model = ECAPA_TDNN_SMALL(feat_dim=1024, feat_type="wavlm_large")
    elif model_name == "hubert_large":
        model = ECAPA_TDNN_SMALL(feat_dim=1024, feat_type="hubert_large_ll60k")
    elif model_name == "wav2vec2_xlsr":
        model = ECAPA_TDNN_SMALL(feat_dim=1024, feat_type="wav2vec2_xlsr")
    else:
        model = ECAPA_TDNN_SMALL(feat_dim=40, feat_type="fbank")

    if checkpoint is not None:
        state_dict = torch.load(
            checkpoint, map_location="cpu", weights_only=True
        )  # safe: plain state-dict, no TorchScript code tree
        model.load_state_dict(state_dict["model"], strict=False)
    return model


def get_emb(wav, model, device="cpu", sample_rate=16000):
    """Extract speaker embedding from a single audio path."""
    wav_data, sr = sf.read(wav)
    wav_tensor = torch.from_numpy(wav_data).unsqueeze(0).float().to(device)

    if sr != sample_rate:
        resample = Resample(orig_freq=sr, new_freq=sample_rate).to(device)
        wav_tensor = resample(wav_tensor)

    with torch.no_grad():
        emb = model(wav_tensor)
        emb = emb.squeeze(0).detach().cpu().numpy()
    return emb


def generate_embs_file(args: tuple, device="cpu", sample_rate=16000, model=None):
    file, out_path = args
    import time

    s_t = time.time()
    emb = get_emb(file, model, device, sample_rate)
    print(f"process {file} cost {time.time() - s_t}")
    np.save(out_path, emb)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir")
    parser.add_argument("--output_dir")
    parser.add_argument(
        "--device",
        default=None,
        help="Device: cuda, mps, cpu or auto-detect. Can also set MEANVC_DEVICE env var.",
    )
    parser.add_argument("--num_thread", type=int, default=10)
    args = parser.parse_args()

    wav_dir = args.input_dir
    output = args.output_dir
    device = get_device(args.device)
    print(f"Using device: {device}")
    num_thread = args.num_thread
    print(args)

    # Resolve checkpoint path relative to project root
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    ckpt_path = os.path.join(
        project_root, "assets", "wavLM", "wavlm_large_finetune.pth"
    )

    model = init_model("wavlm_large", ckpt_path)
    model.eval()
    model.to(device)
    print(f"model loaded to {device}")

    os.makedirs(output, exist_ok=True)
    wavs = glob.glob(os.path.join(wav_dir, "*.wav"))
    input_args = []
    for wav in wavs:
        utt = wav.split("/")[-1][:-4]
        out_path = os.path.join(output, utt + ".npy")
        input_args.append((wav, out_path))

    gen_function = partial(
        generate_embs_file, device=device, sample_rate=16000, model=model
    )

    for i in range(len(input_args)):
        gen_function(input_args[i])
