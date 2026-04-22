"""Download all MeanVC assets into the ``assets/`` folder.

Assets are grouped into three categories:

1. **Core models** — DiT backbone, Vocos vocoder, FastU2++ ASR
   Source: HuggingFace ``ASLP-lab/MeanVC``
2. **Speaker verification** — fine-tuned ECAPA-TDNN + WavLM large
   Source: Google Drive (via ``gdown``)
3. **ECAPA config** — NeMo-style speaker encoder config
   Source: Google Drive (via ``gdown``)

Usage::

    python download_ckpt.py              # download everything (default)
    python download_ckpt.py --core       # only HuggingFace core models
    python download_ckpt.py --sv         # only speaker-verification checkpoint
    python download_ckpt.py --ecapa      # only ECAPA-TDNN assets

All files are written to ``assets/`` relative to this script.
Already-present files are skipped unless ``--force`` is passed.

Dependencies: ``huggingface_hub``, ``gdown`` (both listed in requirements.txt).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# HuggingFace core models
# ---------------------------------------------------------------------------

HF_REPO_ID = "ASLP-lab/MeanVC"

#: Files to pull from the HuggingFace repository.
#: Keys are filenames as they appear in the HF repo; values are destination
#: paths relative to assets/.
CORE_FILES: dict[str, str] = {
    "model_200ms.safetensors": "ckpt/model_200ms.safetensors",  # DiT (safetensors)
    "meanvc_200ms.pt":         "ckpt/meanvc_200ms.pt",          # DiT (TorchScript)
    "vocos.pt":                "ckpt/vocos.pt",                  # Vocos vocoder
    "fastu2++.pt":             "ckpt/fastu2++.pt",              # FastU2++ ASR
}

# ---------------------------------------------------------------------------
# Google Drive assets
# ---------------------------------------------------------------------------
# Google Drive file IDs — update these if links expire.
#
# wavlm_large_finetune.pth
#   Fine-tuned ECAPA-TDNN head on WavLM-Large for speaker verification.
#   Source: https://github.com/microsoft/UniSpeech/tree/main/downstreams/speaker_verification
#   Direct GDrive link used in the original MeanVC scripts:
#     https://drive.google.com/file/d/1-aE1NfzpRCLxA4GUxX9ITI3F9LlbtEGP
SV_GDRIVE_ID = "1-aE1NfzpRCLxA4GUxX9ITI3F9LlbtEGP"
SV_DEST = "wavLM/wavlm_large_finetune.pth"

# ECAPA-TDNN NeMo checkpoint + config
#   Source: NVIDIA NeMo speaker verification model
#   (IDs are placeholders — set --ecapa-gdrive-pt-id and --ecapa-gdrive-cfg-id
#    if you have the correct GDrive links)
ECAPA_PT_GDRIVE_ID: str | None = None   # e.g. "1AbCdEfGhIjKlMnOpQrStUvWx"
ECAPA_CFG_GDRIVE_ID: str | None = None
ECAPA_PT_DEST = "ecapa/ecapa_tdnn.pt"
ECAPA_CFG_DEST = "ecapa/ecapa_tdnn_config.yaml"


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _skip(dest: Path) -> bool:
    """Return True and print a skip message if the file already exists."""
    if dest.exists():
        print(f"  ⊘ {dest}  (already exists, skipping)")
        return True
    return False


def _download_hf(assets: Path, force: bool = False) -> None:
    """Download core models from the HuggingFace Hub (ASLP-lab/MeanVC)."""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        raise SystemExit("huggingface_hub is not installed. Run: pip install huggingface_hub")

    for hf_filename, rel_dest in CORE_FILES.items():
        dest = assets / rel_dest
        if not force and dest.exists():
            print(f"  ⊘ {dest}  (already exists, skipping)")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"  ↓ Downloading {hf_filename} from {HF_REPO_ID} …")
        tmp = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=hf_filename,
            repo_type="model",
            local_dir=str(dest.parent),
            local_dir_use_symlinks=False,
        )
        # hf_hub_download writes to a cache and returns the path; if it
        # didn't land at dest already, copy it there.
        tmp_path = Path(tmp)
        if tmp_path.resolve() != dest.resolve():
            import shutil
            shutil.copy2(tmp, dest)
        print(f"  ✓ {dest}")


def _gdrive_download(file_id: str, dest: Path, desc: str = "") -> None:
    """Download a single file from Google Drive using gdown."""
    try:
        import gdown
    except ImportError:
        raise SystemExit("gdown is not installed. Run: pip install gdown")

    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://drive.google.com/uc?id={file_id}"
    label = desc or dest.name
    print(f"  ↓ Downloading {label} from Google Drive …")
    gdown.download(url, str(dest), quiet=False)
    # gdown.download(url, str(dest), quiet=False, fuzzy=True)
    if dest.exists():
        print(f"  ✓ {dest}")
    else:
        print(f"  ✗ Download failed for {label}. Check the GDrive file ID.")


def _download_sv(assets: Path, gdrive_id: str | None = None, force: bool = False) -> None:
    """Download the WavLM ECAPA-TDNN speaker-verification checkpoint."""
    dest = assets / SV_DEST
    if not force and _skip(dest):
        return

    fid = gdrive_id or SV_GDRIVE_ID
    if not fid:
        print(
            f"  ⚠ No Google Drive ID for speaker-verification checkpoint.\n"
            f"    Manually place wavlm_large_finetune.pth in {dest.parent}\n"
            f"    or pass --sv-gdrive-id <ID>"
        )
        return
    _gdrive_download(fid, dest, desc="wavlm_large_finetune.pth")


def _download_ecapa(
    assets: Path,
    pt_id: str | None = None,
    cfg_id: str | None = None,
    force: bool = False,
) -> None:
    """Download the ECAPA-TDNN NeMo checkpoint and config."""
    pt_dest = assets / ECAPA_PT_DEST
    cfg_dest = assets / ECAPA_CFG_DEST

    for dest, fid, name in [
        (pt_dest,  pt_id  or ECAPA_PT_GDRIVE_ID,  "ecapa_tdnn.pt"),
        (cfg_dest, cfg_id or ECAPA_CFG_GDRIVE_ID,  "ecapa_tdnn_config.yaml"),
    ]:
        if not force and _skip(dest):
            continue
        if not fid:
            print(
                f"  ⚠ No Google Drive ID for {name}.\n"
                f"    Manually place {name} in {dest.parent}\n"
                f"    or pass --ecapa-gdrive-pt-id / --ecapa-gdrive-cfg-id"
            )
            continue
        _gdrive_download(fid, dest, desc=name)


# ---------------------------------------------------------------------------
# Asset verification
# ---------------------------------------------------------------------------

def verify_assets(assets: Path) -> None:
    """Print a summary of which assets are present and which are missing."""
    expected = {
        "ckpt/model_200ms.safetensors": "DiT checkpoint (safetensors)",
        "ckpt/meanvc_200ms.pt":         "DiT checkpoint (TorchScript)",
        "ckpt/vocos.pt":                "Vocos vocoder",
        "ckpt/fastu2++.pt":             "FastU2++ ASR",
        "wavLM/wavlm_large_finetune.pth": "WavLM ECAPA-TDNN (speaker verification)",
        "ecapa/ecapa_tdnn.pt":          "ECAPA-TDNN NeMo checkpoint",
        "ecapa/ecapa_tdnn_config.yaml": "ECAPA-TDNN NeMo config",
    }
    print("\n=== Asset Verification ===")
    all_ok = True
    for rel, desc in expected.items():
        p = assets / rel
        status = "✓" if p.exists() else "✗ MISSING"
        if not p.exists():
            all_ok = False
        size = f"  ({p.stat().st_size / 1e6:.1f} MB)" if p.exists() else ""
        print(f"  {status}  {rel}{size}  — {desc}")
    print()
    if all_ok:
        print("All assets present ✓")
    else:
        print("Some assets are missing. Run download_ckpt.py to fetch them.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download MeanVC assets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Destination
    parser.add_argument(
        "--assets-dir",
        default=str(Path(__file__).parent / "assets"),
        help="Root assets folder",
    )
    # What to download
    parser.add_argument("--core",  action="store_true", help="Download HuggingFace core models only")
    parser.add_argument("--sv",    action="store_true", help="Download speaker-verification checkpoint only")
    parser.add_argument("--ecapa", action="store_true", help="Download ECAPA-TDNN assets only")
    parser.add_argument("--all",   action="store_true", help="Download everything (default behaviour)")
    # Override GDrive IDs
    parser.add_argument("--sv-gdrive-id",        default=None, help="GDrive file ID for wavlm_large_finetune.pth")
    parser.add_argument("--ecapa-gdrive-pt-id",  default=None, help="GDrive file ID for ecapa_tdnn.pt")
    parser.add_argument("--ecapa-gdrive-cfg-id", default=None, help="GDrive file ID for ecapa_tdnn_config.yaml")
    # Force re-download
    parser.add_argument("--force",  action="store_true", help="Re-download even if files already exist")
    # Verify only
    parser.add_argument("--verify", action="store_true", help="Only check which assets are present (no download)")

    args = parser.parse_args()
    assets = Path(args.assets_dir)

    if args.verify:
        verify_assets(assets)
        return

    # Default: download everything unless a specific flag is given
    any_explicit = args.core or args.sv or args.ecapa
    do_core  = args.all or args.core  or not any_explicit
    do_sv    = args.all or args.sv    or not any_explicit
    do_ecapa = args.all or args.ecapa or not any_explicit

    if do_core:
        print("=== Downloading core models from HuggingFace ===")
        _download_hf(assets, force=args.force)

    if do_sv:
        print("=== Downloading speaker-verification checkpoint ===")
        _download_sv(assets, gdrive_id=args.sv_gdrive_id, force=args.force)

    if do_ecapa:
        print("=== Downloading ECAPA-TDNN assets ===")
        _download_ecapa(
            assets,
            pt_id=args.ecapa_gdrive_pt_id,
            cfg_id=args.ecapa_gdrive_cfg_id,
            force=args.force,
        )

    verify_assets(assets)
    print(f"\nAssets directory: {assets.resolve()}")


if __name__ == "__main__":
    main()
