"""Simple training test - bypass Trainer class entirely."""

import os

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import sys
import json
import torch
from torch.utils.data import DataLoader

from src.model import DiT, MeanFlow
from src.dataset.dataset import DiffusionDataset
from src.utils.audio import get_device
from accelerate import Accelerator


def main():
    device = get_device()
    print(f"Device: {device}")

    is_mps = str(device) == "mps"
    mixed_precision = "no" if is_mps else "fp16"

    # Create dataset
    file_lst = DiffusionDataset.init_data("test_data/train.list")
    dd = DiffusionDataset(
        file_lst,
        feature_list=["bn", "mel", "xvector"],
        additional_feature_list=["inputs_length", "prompt"],
        feature_pad_values=[0.0, -1.0, 0.0],
        max_len=1000,
    )
    print(f"Dataset length: {len(dd)}")

    loader = DataLoader(
        dd, batch_size=1, shuffle=True, num_workers=0, collate_fn=dd.custom_collate_fn
    )
    print("DataLoader created")

    # Create model
    with open("src/config/config_200ms.json") as f:
        cfg = json.load(f)
    model = DiT(**cfg["model"])
    print("Model created")

    # Create accelerator - NO DDP for MPS
    if is_mps:
        accelerator = Accelerator(
            gradient_accumulation_steps=1,
            mixed_precision=mixed_precision,
        )
    else:
        from accelerate.utils import DistributedDataParallelKwargs

        accelerator = Accelerator(
            gradient_accumulation_steps=1,
            mixed_precision=mixed_precision,
            kwargs_handlers=[
                DistributedDataParallelKwargs(find_unused_parameters=False)
            ],
        )

    print(f"Accelerator device: {accelerator.device}")
    print(f"Num processes: {accelerator.num_processes}")

    # Prepare
    model, loader = accelerator.prepare(model, loader)
    print("Prepare done")

    meanflow = MeanFlow(
        flow_ratio=0.5,
        time_dist=["lognorm", -0.4, 1.0],
        cfg_ratio=0.1,
        cfg_scale=2.0,
        cfg_uncond="u",
        p=0.5,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    print("Starting training loop...")

    for i, batch in enumerate(loader):
        print(f"Got batch {i + 1}")
        with accelerator.accumulate(model):
            diff_loss, mse_val = meanflow.loss(
                model,
                x=batch["mel"],
                bn=batch["bn"],
                spks=batch["xvector"],
                prompts=batch["prompt"],
                inputs_length=batch["inputs_length"],
            )
            accelerator.backward(diff_loss)
            optimizer.step()
            optimizer.zero_grad()

        print(f"Step {i + 1}: loss={diff_loss.item():.4f}")

        if i >= 1:  # Just 2 iterations
            break

    print("Done!")


if __name__ == "__main__":
    main()
