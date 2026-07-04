"""Benchmark the engine's trajectory-refinement modes on a held-out TUM sequence.

Estela's per-frame depth + predicted relative pose (own_engine.reconstruct pass 1) feed a refinement ladder:
raw model chain -> frame-to-frame ICP (shipped default) -> WINDOWED multi-frame BA (LIDAR3D_OWN_WINDOW) -> GLOBAL
pose-graph + loop closure (LIDAR3D_OWN_GLOBAL). Only the ICP chain is benchmarked in training; the windowed BA and
global PGO have never been scored on the held-out long_office. This runs pass 1 once, then re-runs
_refine_trajectory under each mode and reports the umeyama-aligned ATE, so we can see whether the windowed BA
beats the 0.28 m ICP chain (P0.1 of the improvement plan). Inference only, no training.

Run: PYTHONPATH=data-pipeline python -m lidar3dlab.train.eval_refine_modes --seq long_office --max_frames 240
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from ..model.nets.own_depthpose import OwnDepthPose
from .dataset_tum import TUMPairs, list_sequences
from .train_depthpose import umeyama_ate

# env keys the refinement ladder reads; reset all of them before each mode so a mode never leaks into the next
_KEYS = ["LIDAR3D_OWN_ICP", "LIDAR3D_OWN_WINDOW", "LIDAR3D_OWN_GLOBAL", "LIDAR3D_OWN_WIN"]
_MODES = {
    "raw":    {"LIDAR3D_OWN_ICP": "0"},                                            # no open3d: raw model chain
    "icp":    {"LIDAR3D_OWN_ICP": "1"},                                            # shipped default
    "window": {"LIDAR3D_OWN_ICP": "1", "LIDAR3D_OWN_WINDOW": "1"},                 # windowed multi-frame BA
    "global": {"LIDAR3D_OWN_ICP": "1", "LIDAR3D_OWN_GLOBAL": "1"},                 # global PGO + loop closure
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default="long_office", help="substring picking the TUM sequence")
    ap.add_argument("--max_frames", type=int, default=240)
    ap.add_argument("--stride", type=int, default=0, help="frame stride; 0 = auto to hit ~max_frames")
    ap.add_argument("--conf_q", type=float, default=0.65)
    ap.add_argument("--max_d", type=float, default=6.0)
    ap.add_argument("--win", type=int, default=5, help="temporal window for the windowed BA")
    ap.add_argument("--modes", default="raw,icp,window,global")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seq = next((s for s in list_sequences() if args.seq in s), None)
    if not seq:
        raise SystemExit(f"no TUM sequence matching '{args.seq}' under LIDAR3D_DATA_ROOT/train/tum-rgbd")

    ckpt = Path(os.environ.get("LIDAR3D_MODELS_ROOT", "models")) / "own-depthpose" / "own-depthpose.pt"
    ck = torch.load(str(ckpt), map_location="cpu")
    size = int(ck.get("size", 224))
    model = OwnDepthPose(base=int(ck.get("base", 32)), max_depth=float(ck.get("max_depth", 10.0)),
                         backbone=str(ck.get("backbone", "scratch")), pretrained=False,
                         pose_head=str(ck.get("pose_head", "siamese")))
    model.load_state_dict(ck["model"])
    model = model.to(device).eval()

    ds = TUMPairs(seq, image_size=size)          # gives GT-associated frames (rgb_fn, depth_fn, c2w_gt)
    stride = args.stride or 1                     # CONSECUTIVE frames by default: the pose head was trained on
    sel = ds.frames[::stride][:args.max_frames]   # adjacent pairs, so a large stride is out-of-distribution
    K = ds._K()
    gt_c = np.asarray([f[2][:3, 3] for f in sel])

    def load(fn: str) -> np.ndarray:
        im = Image.open(ds.seq_dir / fn).convert("RGB").resize((size, size), Image.BILINEAR)
        return np.asarray(im, np.float32) / 255.0

    rgbs = [load(f[0]) for f in sel]
    n = len(rgbs)
    kt = torch.from_numpy(np.ascontiguousarray(K, np.float32))[None].to(device)
    depths, confs, model_rels = [], [], []
    with torch.no_grad():                        # pass 1, exactly as own_engine.reconstruct
        for i in range(n):
            t0 = torch.from_numpy(rgbs[i].transpose(2, 0, 1))[None].to(device)
            t1 = torch.from_numpy(rgbs[min(i + 1, n - 1)].transpose(2, 0, 1))[None].to(device)
            out = model(t0, t1, k=kt)
            depths.append(out["depth0"][0, 0].float().cpu().numpy())
            confs.append(np.exp(-out["logvar0"][0, 0].float().cpu().numpy()))
            model_rels.append(out["rel_pose"][0].float().cpu().numpy())

    from ..model.own_engine import _refine_trajectory
    print(f"seq={Path(seq).name} frames={n} size={size} backbone={ck.get('backbone')} "
          f"pose_head={ck.get('pose_head')} conf_q={args.conf_q} max_d={args.max_d} win={args.win}")
    results = {}
    for mode in args.modes.split(","):
        for k in _KEYS:                          # reset, then set this mode's flags
            os.environ.pop(k, None)
        for k, v in _MODES[mode].items():
            os.environ[k] = v
        if mode == "window":
            os.environ["LIDAR3D_OWN_WIN"] = str(args.win)
        c2ws = _refine_trajectory(depths, confs, K, list(model_rels), args.conf_q, args.max_d)
        c = np.asarray([p[:3, 3] for p in c2ws])
        m = min(len(c), len(gt_c))
        ate = umeyama_ate(c[:m], gt_c[:m])
        results[mode] = ate
        print(f"  {mode:8s} ATE = {ate:.4f} m")

    base = results.get("icp")
    best = min(results, key=results.get)
    print(f"BEST = {best} ({results[best]:.4f} m)" + (
        f"  |  vs icp {base:.4f} m -> {(base - results[best]) / base * 100:+.1f}%" if base else ""))


if __name__ == "__main__":
    main()
