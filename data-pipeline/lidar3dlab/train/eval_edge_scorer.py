"""E4 ship-rule A/B: end-to-end windowed ATE with scorer-weighted edges vs the deployed
inlier-count baseline, on the SAME five held-out TUM scenes as probe I1.

Both arms share ONE memoized correspondence front-end per scene (identical matches, identical
edges, identical PGO solver): the ONLY difference is the per-edge weight, so the measured delta
is attributable to the scorer alone. Pre-committed rule (design doc 2026-07-11, the I1
protocol): SHIP iff ATE improves on >= 4/5 held-out scenes; a wash KILLS it (the LightGlue
lesson: isolated wins do not count).

    PYTHONPATH=data-pipeline python -m lidar3dlab.train.eval_edge_scorer --max_frames 240
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
from PIL import Image

from ..model import rgbd_engine
from ..model.edge_scorer import load_scorer
from .dataset_tum import TUMPairs, list_sequences
from .edge_dataset import HELD_OUT
from .train_depthpose import umeyama_ate


def run_scene(seq_dir: str, scorer, max_frames: int, size: int = 224) -> tuple[float, float, int]:
    ds = TUMPairs(seq_dir, image_size=size)
    frames = ds.frames[:max_frames] if max_frames else ds.frames
    n = len(frames)
    K = ds._K()

    def load_rgb(fn: str) -> np.ndarray:
        im = Image.open(ds.seq_dir / fn).convert("RGB").resize((size, size), Image.BILINEAR)
        return np.asarray(im, np.float32) / 255.0

    rgbs_u8 = [(load_rgb(f[0]) * 255).astype(np.uint8) for f in frames]
    depths = [ds._load_depth(f[1]) for f in frames]
    gt_c = np.asarray([f[2][:3, 3] for f in frames])

    raw_rel = rgbd_engine.make_rel_pose(rgbs_u8, depths, K, size)
    cache: dict[tuple[int, int], object] = {}

    def rel(i: int, j: int):
        if (i, j) not in cache:
            cache[(i, j)] = raw_rel(i, j)
        return cache[(i, j)]

    ates = []
    for arm_scorer in (None, scorer):
        c2ws, _fallbacks = rgbd_engine._trajectory(rel, n, arm_scorer)
        c = np.asarray([p[:3, 3] for p in c2ws])
        m = min(len(c), len(gt_c))
        ates.append(umeyama_ate(c[:m], gt_c[:m]))
    return ates[0], ates[1], n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max_frames", type=int, default=240)
    args = ap.parse_args()

    os.environ.pop("LIDAR3D_EDGE_SCORER", None)      # arms are passed explicitly; env must not leak
    scorer = None
    from ..model.edge_scorer import scorer_path
    if scorer_path().exists():
        os.environ["LIDAR3D_EDGE_SCORER"] = "1"
        scorer = load_scorer()
        os.environ.pop("LIDAR3D_EDGE_SCORER", None)
    if scorer is None:
        raise SystemExit("no exported scorer (run train_edge_scorer first)")

    scenes = [s for s in list_sequences()
              if Path(s).name.replace("rgbd_dataset_", "") in HELD_OUT]
    if len(scenes) != len(HELD_OUT):
        raise SystemExit(f"expected the {len(HELD_OUT)} I1 scenes on disk, found {len(scenes)}")

    wins = 0
    rows = []
    for seq in scenes:
        base, scored, n = run_scene(seq, scorer, args.max_frames)
        delta = (base - scored) / base * 100.0 if base > 0 else 0.0
        wins += int(scored < base)
        rows.append((Path(seq).name.replace("rgbd_dataset_", ""), n, base, scored, delta))
        print(f"{rows[-1][0]:34s} frames={n:4d} baseline={base:.4f} m scorer={scored:.4f} m ({delta:+.1f}%)")

    verdict = "SHIP" if wins >= 4 else "DO-NOT-SHIP"
    print(f"\nscenes improved: {wins}/{len(scenes)}  ->  {verdict} (rule: >= 4/5, pre-committed)")
    print("| scene | frames | baseline ATE (m) | scorer ATE (m) | delta |")
    print("|---|---|---|---|---|")
    for name, n, base, scored, delta in rows:
        print(f"| {name} | {n} | {base:.4f} | {scored:.4f} | {delta:+.1f}% |")


if __name__ == "__main__":
    main()
