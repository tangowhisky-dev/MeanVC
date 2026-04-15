"""Training test script - runs 2 iterations to verify MPS device support."""

import sys
import os
import json
import argparse
import torch
from src.model import DiT, Trainer
from src.utils.audio import get_device

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-config", type=str, default="src/config/config_200ms.json"
    )
    parser.add_argument("--exp-name", type=str, default="test_run")
    parser.add_argument("--dataset-path", type=str, default="test_data/train.list")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--max-len", type=int, default=1000)
    parser.add_argument("--feature-list", type=str, default="bn mel xvector")
    parser.add_argument(
        "--additional-feature-list", type=str, default="inputs_length prompt"
    )
    parser.add_argument("--feature-pad-values", type=str, default="0. -1.0 0.")
    parser.add_argument("--flow-ratio", type=float, default=0.5)
    parser.add_argument("--cfg-ratio", type=float, default=0.1)
    parser.add_argument("--cfg-scale", type=float, default=2.0)
    parser.add_argument("--p", type=float, default=0.5)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--cfg-strength", type=float, default=2.0)
    parser.add_argument("--chunk-size", type=int, default=16)
    parser.add_argument("--result-dir", type=str, default="test_results")
    parser.add_argument("--save-per-updates", type=int, default=1000)
    parser.add_argument("--reset-lr", type=int, default=0)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--num-warmup-updates", type=int, default=10)
    parser.add_argument("--resumable-with-seed", type=int, default=0)
    parser.add_argument("--grad-accumulation-steps", type=int, default=1)
    parser.add_argument("--grad-ckpt", type=int, default=0)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--last-per-steps", type=int, default=1000)
    args = parser.parse_args()

    args.feature_pad_values = args.feature_pad_values.split()



    device = get_device()
    print(f"Device selected: {device}")
    print(f"MPS device: {str(device) == 'mps'}")

    if str(device) == "mps":
        print("MPS detected - disabling AMP and forcing float32")

    with open(args.model_config) as f:
        model_config = json.load(f)

    model = DiT(**model_config["model"])
    total_params = sum(p.numel() for p in model.parameters()) / 1000000
    print(f"Model params: {total_params:.2f}M")

    for name, param in model.named_parameters():
        if param.dtype != torch.float32:
            print(f"WARNING: {name} has dtype {param.dtype}")

    trainer = Trainer(
        model,
        args,
        args.epochs,
        args.learning_rate,
        num_warmup_updates=args.num_warmup_updates,
        save_per_updates=args.save_per_updates,
        checkpoint_path=f"ckpts/{args.exp_name}",
        grad_accumulation_steps=args.grad_accumulation_steps,
        max_grad_norm=1.0,
        wandb_project="meanvc",
        wandb_run_name=args.exp_name,
        wandb_resume_id=None,
        last_per_steps=args.last_per_steps,
        bnb_optimizer=False,
        reset_lr=args.reset_lr,
        batch_size=args.batch_size,
        grad_ckpt=args.grad_ckpt,
        device=device,
    )

    print(f"Trainer device: {trainer.device}")
    print(f"Accelerator mixed precision: {trainer.accelerator.state.mixed_precision}")

    print("\nRunning 2 training iterations...")
    trainer.train(resumable_with_seed=0)
    print("\nTraining test completed successfully!")


if __name__ == "__main__":
    main()
