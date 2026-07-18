"""E4: build the labeled edge dataset from the TRAIN TUM sequences (GT labels are free).

Walks each sequence with EXACTLY the engine's window pattern (same _WIN/_SKIP, same stride,
same front-end via make_rel_pose) so the training distribution IS the deployment distribution
(the I1 lesson: isolated probes lie). Per present edge: the N_FEAT feature vector with the
chain-gap entries filled from the window's consecutive measurements, and the GT label
log1p(err_t + err_r_rad) against the GT relative pose.

The five I1 held-out scenes (desk, office, desk2/freiburg2_desk, xyz, pioneer) are REFUSED here
by name: they exist only for the end-to-end A/B (eval_edge_scorer).

    PYTHONPATH=data-pipeline python -m lidar3dlab.train.edge_dataset --max_frames 240
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from ..model.edge_scorer import chain_gap, relpose_error
from ..model.rgbd_engine import _SKIP, _WIN, make_rel_pose
from .dataset_tum import TUMPairs, list_sequences

# The I1 protocol's held-out five (performance-investment-plan 2026-07-06): never in training.
HELD_OUT = ("freiburg1_desk", "freiburg3_long_office_household", "freiburg2_desk",
            "freiburg1_xyz", "freiburg2_pioneer_slam")
# freiburg2_desk_with_person contains freiburg2_desk as a substring: match exactly on the tail.


def is_held_out(seq_dir: str) -> bool:
    name = Path(seq_dir).name.replace("rgbd_dataset_", "")
    return name in HELD_OUT


def build_sequence(seq_dir: str, max_frames: int, size: int = 224) -> tuple[np.ndarray, np.ndarray]:
    """All window edges of one sequence -> (features [E, N_FEAT], labels [E])."""
    from ..model.nets.window_ba import window_edges

    ds = TUMPairs(seq_dir, image_size=size)
    frames = ds.frames[:max_frames] if max_frames else ds.frames
    n = len(frames)
    if n < _WIN + 1:
        return np.zeros((0, 11), np.float32), np.zeros((0,), np.float32)
    K = ds._K()

    def load_rgb(fn: str) -> np.ndarray:
        im = Image.open(ds.seq_dir / fn).convert("RGB").resize((size, size), Image.BILINEAR)
        return np.asarray(im, np.float32) / 255.0

    rgbs_u8 = [(load_rgb(f[0]) * 255).astype(np.uint8) for f in frames]
    depths = [ds._load_depth(f[1]) for f in frames]
    gt_c2w = [f[2] for f in frames]
    rel_pose = make_rel_pose(rgbs_u8, depths, K, size)

    pairs = window_edges(_WIN, skip=_SKIP).tolist()
    feats_out, labels_out = [], []
    s = 0
    while s + _WIN <= n:                                    # the engine's window stride (_WIN - 1)
        results = {(a, b): rel_pose(s + a, s + b) for (a, b) in pairs}
        consecutive = [results.get((k, k + 1)) for k in range(_WIN - 1)]
        for (a, b) in pairs:
            e = results[(a, b)]
            if e is None:
                continue                                     # absent edges carry no supervision
            fv = e[2].copy()
            if b - a > 1:
                span = [c[0] if c is not None else None for c in consecutive[a:b]]
                fv[9], fv[10] = chain_gap(e[0], span)
            gt_rel = np.linalg.inv(gt_c2w[s + a]) @ gt_c2w[s + b]
            err_t, err_r = relpose_error(e[0], gt_rel)
            feats_out.append(fv)
            labels_out.append(np.log1p(err_t + err_r))      # 1 m <-> 1 rad lever-arm equivalence (stated)
        s += _WIN - 1
    if not feats_out:
        return np.zeros((0, 11), np.float32), np.zeros((0,), np.float32)
    return np.stack(feats_out).astype(np.float32), np.asarray(labels_out, np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max_frames", type=int, default=240)
    ap.add_argument("--out", default="data/derived/e4-edges")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for seq in list_sequences():
        if is_held_out(seq):
            print(f"held-out (refused for training): {Path(seq).name}")
            continue
        feats, labels = build_sequence(seq, args.max_frames)
        np.savez_compressed(out_dir / f"{Path(seq).name}.npz", feats=feats, labels=labels)
        total += len(labels)
        print(f"{Path(seq).name}: {len(labels)} labeled edges "
              f"(err median {np.expm1(np.median(labels)):.4f})" if len(labels) else f"{Path(seq).name}: 0 edges")
    print(f"total labeled edges: {total} -> {out_dir}")


if __name__ == "__main__":
    main()
