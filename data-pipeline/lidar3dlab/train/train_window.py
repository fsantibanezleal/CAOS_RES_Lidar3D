"""Train the M-C WINDOWED model (model/nets/window_ba.py, #22): per-frame depth + a geometric relative-pose
MEASUREMENT per window edge, so the differentiable window pose-graph solve (window_pgo) can fuse a whole window
of poses into a globally consistent trajectory and beat per-pair accumulation drift.

The training-path pivot. Back-propagating through window_pgo (a second-order differentiable Gauss-Newton solve)
with an untrained head produced a NaN backward. So we DO NOT train through the solver. Instead we supervise the
per-edge measurements DIRECTLY: for every window edge (i,j) (consecutive AND skip) the geo head must predict the
ground-truth relative pose T_i^{-1} T_j. That is a first-order, stable loss. window_pgo is then used forward-only
at inference to fuse the learned edges. The synthetic self-test in window_ba.py already shows that, given good-ish
per-edge measurements, the windowed solve beats a pure consecutive chain; this trainer makes the measurements good
on real data, and the eval below reports both (fused vs chained) so the fusion gain is measured, not assumed.

Run: PYTHONPATH=data-pipeline python -m lidar3dlab.train.train_window --epochs 3 --batch 4 --window 6 --skip 2 \
        --init "$LIDAR3D_MODELS_ROOT/own-depthpose/own-depthpose.pt"
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import ConcatDataset, DataLoader

from ..model.nets.window_ba import WindowDepthPose, window_edges, window_pgo
from .dataset_tum import TartanGroundWindows, tartanground_sequences
from .train_depthpose import depth_loss, umeyama_ate


def edge_gt(poses: torch.Tensor, edges: torch.Tensor) -> torch.Tensor:
    """Ground-truth relative pose T_i^{-1} T_j for every edge. poses: [N,4,4] absolute (frame 0 = identity)."""
    ti = torch.linalg.inv(poses[edges[:, 0]])
    return ti @ poses[edges[:, 1]]


def measurement_loss(z_rel: torch.Tensor, w: torch.Tensor, gt: torch.Tensor,
                     conf_reg: float = 0.02) -> tuple[torch.Tensor, torch.Tensor]:
    """Aleatoric per-edge relative-pose loss: confidence w down-weights an edge's residual but pays a -log w
    price, so the head learns BOTH good measurements and a calibrated confidence for window_pgo to weight by.
    Returns (loss, raw pose error) with the raw error detached for logging."""
    r = (z_rel[:, :3, :3] - gt[:, :3, :3]).pow(2).mean(dim=(1, 2))     # [E] rotation residual
    t = (z_rel[:, :3, 3] - gt[:, :3, 3]).abs().mean(dim=1)             # [E] translation residual
    per = r + t
    wc = w.clamp(min=1e-3)
    loss = (wc * per - conf_reg * torch.log(wc)).mean()
    return loss, per.mean().detach()


def _collate(batch: list[dict]) -> dict:
    return {"rgbs": torch.from_numpy(np.stack([b["rgbs"] for b in batch])),      # [B,N,3,H,W]
            "depths": torch.from_numpy(np.stack([b["depths"] for b in batch])),  # [B,N,H,W]
            "poses": torch.from_numpy(np.stack([b["poses"] for b in batch])),    # [B,N,4,4]
            "K": torch.from_numpy(np.stack([b["K"] for b in batch]))}            # [B,3,3]


@torch.no_grad()
def evaluate(model: WindowDepthPose, seq_dir: str, device: torch.device, size: int, window: int,
             skip: int, max_windows: int) -> dict:
    """Full-trajectory ATE on a held-out sequence, composing overlapping windows (win_stride = window-1, so each
    window shares its first frame with the previous window's last). Reports the window_pgo FUSED trajectory and,
    as an ablation on the SAME measurements, a pure consecutive CHAIN, so the fusion gain is explicit."""
    ds = TartanGroundWindows(seq_dir, image_size=size, window=window, win_stride=window - 1,
                             max_windows=max_windows)
    if len(ds) < 2:
        return {"ate_fused": float("nan"), "ate_chain": float("nan"), "edge_err": float("nan"), "windows": len(ds)}
    edges = window_edges(window, skip=skip).to(device)
    model.eval()
    Gf = np.eye(4)          # running global cam-to-world for the FUSED trajectory
    Gc = np.eye(4)          # running global cam-to-world for the CHAINED trajectory
    pred_f, pred_c = [Gf[:3, 3].copy()], [Gc[:3, 3].copy()]
    gt_c2w = np.eye(4)
    gt_list = [gt_c2w[:3, 3].copy()]
    edge_err_sum, edge_err_n = 0.0, 0
    for wi in range(len(ds)):
        s = ds[wi]
        rgbs = torch.from_numpy(s["rgbs"]).to(device)
        K = torch.from_numpy(s["K"]).to(device)
        gt_poses = torch.from_numpy(s["poses"]).to(device)
        m = model.measure_edges(rgbs, K, edges)
        z, w = m["z_rel"].float(), m["weight"].float()
        edge_err_sum += float((z[:, :3, 3] - edge_gt(gt_poses, edges)[:, :3, 3]).norm(dim=1).mean())
        edge_err_n += 1
        fused = window_pgo(z, edges, w, window, iters=model.iters).cpu().numpy()   # [N,4,4] local, frame0=I
        # chained: compose ONLY the consecutive measurements (what a per-pair estimator does)
        chain = [np.eye(4)]
        zc = z.cpu().numpy()
        z_by_pair = {(int(a), int(b)): zc[idx] for idx, (a, b) in enumerate(edges.cpu().numpy())}
        for f in range(1, window):
            chain.append(chain[-1] @ z_by_pair[(f - 1, f)])
        chain = np.stack(chain)
        gt_np = gt_poses.cpu().numpy()
        for f in range(1, window):                       # append frames 1..N-1 (frame 0 is the shared anchor)
            pred_f.append((Gf @ fused[f])[:3, 3].copy())
            pred_c.append((Gc @ chain[f])[:3, 3].copy())
            gt_list.append((gt_c2w @ gt_np[f])[:3, 3].copy())
        Gf = Gf @ fused[window - 1]                      # advance anchors by the window's last (shared) frame
        Gc = Gc @ chain[window - 1]
        gt_c2w = gt_c2w @ gt_np[window - 1]
    pf, pc, g = np.asarray(pred_f), np.asarray(pred_c), np.asarray(gt_list)
    n = min(len(pf), len(g))
    return {"ate_fused": umeyama_ate(pf[:n], g[:n]), "ate_chain": umeyama_ate(pc[:n], g[:n]),
            "edge_err": edge_err_sum / max(1, edge_err_n), "windows": len(ds)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=4, help="windows per step")
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--window", type=int, default=6, help="frames per window (N)")
    ap.add_argument("--skip", type=int, default=2, help="max skip-edge distance (1=consecutive only)")
    ap.add_argument("--backbone", choices=["resnet18", "dinov2_vits14", "dinov2_vitb14"], default="resnet18")
    ap.add_argument("--base", type=int, default=32, help="depth-decoder width; 32 matches the deployed M8 checkpoint")
    ap.add_argument("--init", type=str, default="", help="warm-start depth+geo from a checkpoint (reuse the M8 depth net)")
    ap.add_argument("--freeze_depth", action="store_true", help="freeze backbone+depth decoder, train ONLY the geo head")
    ap.add_argument("--max_windows", type=int, default=None, help="cap windows per sequence (smoke/quick)")
    ap.add_argument("--pgo_iters", type=int, default=5, help="window_pgo iterations at inference")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--smoke", action="store_true", help="1 tiny step + 1 eval window, no checkpoint")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"
    dtype = torch.bfloat16 if (use_cuda and torch.cuda.get_device_capability()[0] >= 8) else torch.float32
    seqs = tartanground_sequences()
    if not seqs:
        raise SystemExit("no TartanGround sequences under LIDAR3D_DATA_ROOT/train/tartanground (download first)")
    val_seq = seqs[-1]
    train_seqs = seqs[:-1] or seqs
    mw = 4 if args.smoke else args.max_windows
    datasets = [TartanGroundWindows(s, image_size=args.size, window=args.window, max_windows=mw)
                for s in train_seqs]
    train = ConcatDataset(datasets)
    nworkers = 0 if args.smoke else max(0, args.workers)
    dl = DataLoader(train, batch_size=(2 if args.smoke else args.batch), shuffle=True, drop_last=True,
                    num_workers=nworkers, pin_memory=use_cuda, collate_fn=_collate,
                    persistent_workers=(nworkers > 0), prefetch_factor=(4 if nworkers > 0 else None))

    model = WindowDepthPose(backbone=args.backbone, base=args.base, pretrained=True, iters=args.pgo_iters).to(device)
    if args.init:
        sd = torch.load(args.init, map_location="cpu")["model"]
        msd = model.state_dict()
        keep = {k: v for k, v in sd.items() if k in msd and msd[k].shape == v.shape}   # shape-safe: never crash
        model.load_state_dict(keep, strict=False)
        print(f"warm-started {len(keep)}/{len(msd)} tensors from {os.path.basename(args.init)} "
              f"({len(msd) - len(keep)} left at init, e.g. the geo head)")
    if args.freeze_depth:
        for nm, p in model.named_parameters():
            if not nm.startswith("geo"):
                p.requires_grad_(False)
        print(f"froze depth+backbone; trainable={sum(p.numel() for p in model.parameters() if p.requires_grad)/1e6:.2f}M")
    edges = window_edges(args.window, skip=args.skip).to(device)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, args.epochs * max(1, len(dl))))
    print(f"device={device} dtype={dtype} windows={len(train)} val={os.path.basename(val_seq)} "
          f"N={args.window} edges={len(edges)} params={sum(p.numel() for p in model.parameters())/1e6:.2f}M")

    out_dir = Path(os.environ.get("LIDAR3D_MODELS_ROOT", "models")) / "own-depthpose"
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    best = float("inf")
    steps = 0
    for ep in range(1 if args.smoke else args.epochs):
        model.train()
        for b in dl:
            rgbs = b["rgbs"].to(device)          # [B,N,3,H,W]
            depths = b["depths"].to(device)      # [B,N,H,W]
            poses = b["poses"].to(device)        # [B,N,4,4]
            K = b["K"].to(device)                # [B,3,3]
            B = rgbs.shape[0]
            opt.zero_grad(set_to_none=True)
            ld_sum = lp_sum = 0.0
            err_sum = 0.0
            with torch.autocast("cuda", dtype=dtype, enabled=use_cuda):
                loss = rgbs.new_zeros(())
                for wi in range(B):              # loop windows (small B); reuses the exact inference measurement path
                    m = model.measure_edges(rgbs[wi], K[wi], edges)
                    ld = depth_loss(m["depth"].float(), m["logvar"].float(), depths[wi], 10.0)
                    gt = edge_gt(poses[wi], edges).float()
                    lp, err = measurement_loss(m["z_rel"].float(), m["weight"].float(), gt)
                    loss = loss + ld + lp
                    ld_sum += ld.item()
                    lp_sum += lp.item()
                    err_sum += err.item()
                loss = loss / B
            loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
            opt.step()
            if not args.smoke:
                sched.step()
            steps += 1
            if steps % 20 == 0 or args.smoke:
                print(f"ep{ep} step{steps} loss={loss.item():.4f} depth={ld_sum/B:.4f} "
                      f"meas={lp_sum/B:.4f} edge_err={err_sum/B:.4f}m")
            if args.smoke and steps >= 1:
                break
        if args.smoke:
            r = evaluate(model, val_seq, device, args.size, args.window, args.skip, max_windows=2)
            print(f"SMOKE eval: {r}")
            print("SMOKE OK")
            return
        r = evaluate(model, val_seq, device, args.size, args.window, args.skip, max_windows=200)
        improved = r["ate_fused"] < best
        print(f"[epoch {ep}] ATE fused={r['ate_fused']:.4f}m chain={r['ate_chain']:.4f}m "
              f"edge_err={r['edge_err']:.4f}m windows={r['windows']}" + (" (best, saved)" if improved else ""))
        with open(out_dir / "experiments.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _dt.datetime.now().isoformat(timespec="seconds"), "model": "window-mc",
                                "backbone": args.backbone, "epoch": ep, "window": args.window, "skip": args.skip,
                                "ate_fused": round(r["ate_fused"], 4), "ate_chain": round(r["ate_chain"], 4),
                                "edge_err": round(r["edge_err"], 4), "is_best": improved,
                                "val_seq": os.path.basename(val_seq)}) + "\n")
        if improved:
            best = r["ate_fused"]
            ckpt = {"model": model.state_dict(), "backbone": args.backbone, "window": args.window,
                    "skip": args.skip, "pgo_iters": args.pgo_iters, "ate_fused": r["ate_fused"],
                    "ate_chain": r["ate_chain"]}
            torch.save(ckpt, out_dir / f"window-mc-{args.backbone}-{run_id}.pt")
            torch.save(ckpt, out_dir / "window-mc.pt")
    print(f"best ATE fused={best:.4f}m -> {out_dir / 'window-mc.pt'}")


if __name__ == "__main__":
    main()
