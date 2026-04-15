from __future__ import annotations

import os
import random
from collections import defaultdict
from importlib.resources import files
import matplotlib.pylab as plt
import torch
from torch.nn.utils.rnn import pad_sequence

def _is_torchscript_archive(path: str) -> bool:
    """Return True if *path* is a TorchScript ZIP archive (not a plain state-dict).

    TorchScript archives always contain a ``<root>/data.pkl`` entry AND a
    ``<root>/code/`` directory with TorchScript IR files.  Plain
    ``torch.save()`` files contain ``archive/data.pkl`` but NO ``code/``
    directory.

    We detect this by peeking at the ZIP table of contents — zero bytes of
    tensor data are read.
    """
    import zipfile
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        return any("/code/__torch__/" in n for n in names)
    except (zipfile.BadZipFile, OSError):
        return False


def _load_plain_state_dict(path: str, device: str) -> dict:
    """Load a plain ``torch.save()`` state-dict file safely.

    Strategy:
    1.  ``.safetensors`` → ``safetensors.torch.load_file`` (inherently safe,
        no pickle at all).
    2.  ``.pt`` / ``.pth`` that is a **plain state-dict** (no TorchScript
        code tree) → ``torch.load(..., weights_only=True)``.
        ``weights_only=True`` restricts the pickle unpickler to only
        reconstruct tensors + a small whitelist (OrderedDict, etc.).
        It *would* fail on TorchScript archives, but we've already ruled
        those out with ``_is_torchscript_archive()``.

    Returns the raw checkpoint dict (not yet unwrapped for EMA).
    """
    ext = path.rsplit(".", 1)[-1].lower()
    if ext == "safetensors":
        from safetensors.torch import load_file
        return load_file(path)                          # returns {name: tensor}

    # Plain torch.save() file — safe to use weights_only=True because
    # _is_torchscript_archive() already confirmed there's no code/ tree.
    # torch.load with weights_only=True rejects pickle globals outside the
    # tensor / primitive whitelist, so the only things constructed are
    # tensors, OrderedDicts, and primitives — no arbitrary code execution.
    return torch.load(path, map_location=device, weights_only=True)


# load checkpoint
def load_checkpoint(model: torch.nn.Module, ckpt_path: str, device: str, use_ema: bool = True) -> torch.nn.Module:
    """Load model weights from a checkpoint into *model* and return it.

    Handles three formats:

    1. ``.safetensors`` — loaded with ``safetensors.torch.load_file``
       (no pickle, inherently safe, ``weights_only`` not applicable).
    2. Plain ``torch.save(state_dict)`` ``.pt`` / ``.pth`` — loaded with
       ``torch.load(..., weights_only=True)`` after confirming no TorchScript
       code tree is present.
    3. TorchScript archives (``torch.jit.save()``) — these must be loaded
       with ``torch.jit.load()``, not this function.  Passing one here
       raises ``ValueError`` with a clear message.

    ``weights_only=True`` is used for case 2 so that the pickle unpickler
    is restricted to tensors + a small safe whitelist (no ``os``,
    ``subprocess``, ``eval``, etc.).

    Note: half-precision is only applied for CUDA devices.  CPU and MPS
    run in float32 for numerical stability.

    Args:
        model:     The ``nn.Module`` whose parameters will be replaced.
        ckpt_path: Path to the checkpoint file.
        device:    Target device string (``'cpu'``, ``'mps'``, ``'cuda'``, …).
        use_ema:   If True, unwrap EMA weights from ``ema_model_state_dict``.

    Returns:
        The model with loaded weights, moved to *device*.
    """
    if isinstance(device, str) and device.startswith("cuda"):
        model = model.half()

    ext = ckpt_path.rsplit(".", 1)[-1].lower()

    # Guard: reject TorchScript archives early with a helpful message
    if ext != "safetensors" and _is_torchscript_archive(ckpt_path):
        raise ValueError(
            f"load_checkpoint() received a TorchScript archive: {ckpt_path}\n"
            "TorchScript archives must be loaded with torch.jit.load(), not "
            "load_checkpoint().  Use the .safetensors variant for plain weights."
        )

    checkpoint = _load_plain_state_dict(ckpt_path, device)

    if use_ema:
        if ext == "safetensors":
            checkpoint = {"ema_model_state_dict": checkpoint}
        checkpoint["model_state_dict"] = {
            k.replace("ema_model.", ""): v
            for k, v in checkpoint["ema_model_state_dict"].items()
            if k not in ["initted", "step"]
        }
        model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    else:
        if ext == "safetensors":
            checkpoint = {"model_state_dict": checkpoint}
        model.load_state_dict(checkpoint["model_state_dict"], strict=False)

    return model.to(device)





# seed everything
def seed_everything(seed=0):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# helpers

def optimized_scale(positive_flat, negative_flat):
    dot_product = torch.sum(positive_flat * negative_flat, dim=1, keepdim=True)
    squared_norm = torch.sum(negative_flat ** 2, dim=1, keepdim=True) + 1e-8
    st_star = dot_product / squared_norm
    return st_star


def exists(v):
    return v is not None


def default(v, d):
    return v if exists(v) else d


def plot_spectrogram(spectrogram):
    fig, ax = plt.subplots(figsize=(10, 2))
    im = ax.imshow(spectrogram, aspect="auto", origin="lower",
                   interpolation='none')
    plt.colorbar(im, ax=ax)

    fig.canvas.draw()
    plt.close()

    return fig


# tensor helpers


def lens_to_mask(t: int["b"], length: int | None = None) -> bool["b n"]:  # noqa: F722 F821
    if not exists(length):
        length = t.amax()

    seq = torch.arange(length, device=t.device)
    return seq[None, :] < t[:, None]
