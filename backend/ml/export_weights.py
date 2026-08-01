"""Export a trained model.pt (PyTorch state_dict) to a NumPy .npz archive.

The serving path (ml/recommender.py) runs the forward pass in pure NumPy, so the
deployed API never imports torch — that's what keeps cold starts fast and the
memory footprint small enough for a tiny always-on host. torch is only needed to
*train*; this script is the bridge run once after training.

Usage (from backend/, with the training extras installed):
    ../venv/bin/python -m ml.export_weights                 # base checkpoints
    ../venv/bin/python -m ml.export_weights checkpoints/v123 # a retrain dir
"""
import os
import sys

import numpy as np
import torch

WEIGHTS_NAME = "model_weights.npz"


def export_weights(model_path: str, out_path: str) -> str:
    """Convert every tensor in the state_dict to a NumPy array and save them
    under their original keys (e.g. "mlp.0.weight"), so the NumPy engine can look
    each one up by name."""
    state = torch.load(model_path, map_location="cpu")
    arrays = {key: tensor.detach().cpu().numpy() for key, tensor in state.items()}
    np.savez(out_path, **arrays)
    return out_path


def main() -> None:
    base = os.path.dirname(__file__)
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base, "checkpoints")
    model_path = os.path.join(target, "model.pt")
    out_path = os.path.join(target, WEIGHTS_NAME)
    export_weights(model_path, out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
