"""Train OUR own depth+pose model (model/nets/own_depthpose.py) on real TUM RGB-D, on the GPU.

Supervised: aleatoric-weighted metric-depth loss (uses the learned log-variance) + a relative-pose loss
(rotation Frobenius + translation L1). Evaluates ATE on a held-out sequence by accumulating the predicted
relative poses into a trajectory and rigidly aligning it to the ground truth (Umeyama, no scale). Checkpoints to
LIDAR3D_MODELS_ROOT/own-depthpose/. 8 GB-safe (bf16 autocast, image_size 224, small batch).

Run: PYTHONPATH=data-pipeline python -m lidar3dlab.train.train_depthpose --epochs 2 --batch 6
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import ConcatDataset, DataLoader

from ..model.nets.own_depthpose import OwnDepthPose
from .dataset_tum import (ICLPairs, TartanGroundPairs, TUMPairs, icl_sequences, list_sequences,
                          tartanground_sequences)


def depth_loss(pred: torch.Tensor, logvar: torch.Tensor, gt: torch.Tensor, max_depth: float) -> torch.Tensor:
    valid = (gt > 0.1) & (gt < max_depth)
    if valid.sum() < 16:
        return pred.sum() * 0.0
    l1 = (pred.squeeze(1) - gt).abs()
    lv = logvar.squeeze(1)
    loss = (l1 * torch.exp(-lv) + 0.5 * lv)[valid]
    return loss.mean()


def pose_loss(pred: torch.Tensor, gt: torch.Tensor) -> torch.Tensor:
    r = (pred[:, :3, :3] - gt[:, :3, :3]).pow(2).mean()
    t = (pred[:, :3, 3] - gt[:, :3, 3]).abs().mean()
    return r + t


def _ssim(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Lightweight SSIM (3x3 avg-pool windows) -> per-pixel structural dissimilarity in [0,1]."""
    pool = torch.nn.functional.avg_pool2d
    mu_a, mu_b = pool(a, 3, 1, 1), pool(b, 3, 1, 1)
    va = pool(a * a, 3, 1, 1) - mu_a * mu_a
    vb = pool(b * b, 3, 1, 1) - mu_b * mu_b
    vab = pool(a * b, 3, 1, 1) - mu_a * mu_b
    c1, c2 = 0.01 ** 2, 0.03 ** 2
    ssim = ((2 * mu_a * mu_b + c1) * (2 * vab + c2)) / ((mu_a ** 2 + mu_b ** 2 + c1) * (va + vb + c2))
    return ((1 - ssim) / 2).clamp(0, 1)


def photometric_loss(rgb0: torch.Tensor, rgb1: torch.Tensor, depth0: torch.Tensor,
                     rel_pose: torch.Tensor, K: torch.Tensor) -> torch.Tensor:
    """Self-supervised reprojection: warp rgb1 into frame-0 using the PREDICTED depth0 + relative pose, and
    penalize the photometric mismatch (SSIM + L1). rel_pose maps cam1->cam0 (frame t+1 in frame t), so cam0->cam1
    is its inverse. Gradients flow to both depth and pose. Auto-masks invalid/behind-camera pixels."""
    B, _, H, W = rgb0.shape
    dev = rgb0.device
    vv, uu = torch.meshgrid(torch.arange(H, device=dev), torch.arange(W, device=dev), indexing="ij")
    pix = torch.stack([uu.float(), vv.float(), torch.ones_like(uu, dtype=torch.float32)], 0).reshape(3, -1)  # [3,HW]
    Kinv = torch.inverse(K.float())                                   # [B,3,3]
    cam0 = (Kinv @ pix).reshape(B, 3, H, W) * depth0                  # [B,3,H,W] back-projected to cam0
    inv = torch.inverse(rel_pose.float())                            # cam0 -> cam1
    R, t = inv[:, :3, :3], inv[:, :3, 3:4]
    cam1 = (R @ cam0.reshape(B, 3, -1) + t).reshape(B, 3, H, W)       # [B,3,H,W] in cam1
    z = cam1[:, 2:3].clamp(min=1e-3)
    proj = (K.float() @ (cam1.reshape(B, 3, -1) / z.reshape(B, 1, -1))).reshape(B, 3, H, W)
    gx = 2 * proj[:, 0] / (W - 1) - 1
    gy = 2 * proj[:, 1] / (H - 1) - 1
    grid = torch.stack([gx, gy], -1)                                 # [B,H,W,2]
    warped = torch.nn.functional.grid_sample(rgb1, grid, align_corners=True, padding_mode="border")
    valid = (cam1[:, 2:3] > 1e-3) & (gx.abs() <= 1).unsqueeze(1) & (gy.abs() <= 1).unsqueeze(1) & (depth0 > 0.1)
    l1 = (warped - rgb0).abs().mean(1, keepdim=True)
    ssim = _ssim(warped, rgb0).mean(1, keepdim=True)
    per = 0.15 * l1 + 0.85 * ssim
    v = valid.float()
    return (per * v).sum() / v.sum().clamp(min=1.0)


def smoothness_loss(depth: torch.Tensor, rgb: torch.Tensor) -> torch.Tensor:
    """Edge-aware depth smoothness (Monodepth2-style): penalize depth gradients, down-weighted where the image
    has edges. Makes the depth (and thus the point cloud) cleaner / less noisy."""
    d = depth / (depth.mean(dim=[2, 3], keepdim=True) + 1e-6)
    dx = (d[:, :, :, :-1] - d[:, :, :, 1:]).abs()
    dy = (d[:, :, :-1, :] - d[:, :, 1:, :]).abs()
    g = rgb.mean(1, keepdim=True)
    wx = torch.exp(-(g[:, :, :, :-1] - g[:, :, :, 1:]).abs() * 10)
    wy = torch.exp(-(g[:, :, :-1, :] - g[:, :, 1:, :]).abs() * 10)
    return (dx * wx).mean() + (dy * wy).mean()


def umeyama_ate(pred_c: np.ndarray, gt_c: np.ndarray) -> float:
    """RMS ATE after a rigid (R,t) alignment of the predicted trajectory to the GT (no scale)."""
    mp, mg = pred_c.mean(0), gt_c.mean(0)
    P, G = pred_c - mp, gt_c - mg
    U, _, Vt = np.linalg.svd(P.T @ G)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1, 1, d]) @ U.T
    aligned = (R @ P.T).T + mg
    return float(np.sqrt(((aligned - gt_c) ** 2).sum(1).mean()))


@torch.no_grad()
def evaluate(model: OwnDepthPose, seq_dir: str, device: torch.device, size: int, max_pairs: int) -> float:
    ds = TUMPairs(seq_dir, image_size=size, max_pairs=max_pairs)
    if len(ds) < 4:
        return float("nan")
    model.eval()
    c2w = np.eye(4)
    pred_c, gt_c = [c2w[:3, 3].copy()], []
    gt_accum = np.eye(4)
    for i in range(len(ds)):
        s = ds[i]
        r0 = torch.from_numpy(s["rgb0"])[None].to(device)
        r1 = torch.from_numpy(s["rgb1"])[None].to(device)
        rel = model(r0, r1)["rel_pose"][0].float().cpu().numpy()
        c2w = c2w @ rel
        pred_c.append(c2w[:3, 3].copy())
        gt_accum = gt_accum @ s["rel_pose"]
        gt_c.append(gt_accum[:3, 3].copy())
    pred_c = np.asarray(pred_c[:-1])
    gt_c = np.asarray(gt_c)
    n = min(len(pred_c), len(gt_c))
    return umeyama_ate(pred_c[:n], gt_c[:n])


def _log_experiment(out_dir: Path, rec: dict) -> None:
    """Append one training epoch's result to models/own-depthpose/experiments.jsonl so the full history of every
    model/experiment is preserved (fed into docs/experiments + the web Experiments page). Never truncates."""
    import datetime
    import json
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), **rec}
    with open(out_dir / "experiments.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--max_pairs", type=int, default=None, help="cap pairs per sequence (smoke test)")
    ap.add_argument("--photo_w", type=float, default=0.0, help="self-supervised photometric loss weight (0=off)")
    ap.add_argument("--base", type=int, default=32, help="model width (channels); bigger = more capacity")
    ap.add_argument("--smooth_w", type=float, default=0.0, help="edge-aware depth smoothness weight (0=off)")
    ap.add_argument("--use_icl", action="store_true", help="also train on ICL-NUIM (synthetic, perfect GT depth)")
    ap.add_argument("--use_tartan", action="store_true", help="also train on TartanGround (synthetic, perfect depth+pose; far/sky masked to the model's range)")
    ap.add_argument("--seqs", type=str, default="", help="comma-separated substrings; keep only matching TUM train sequences (e.g. 'freiburg1_desk,freiburg1_xyz'). Empty = all discovered")
    ap.add_argument("--backbone", choices=["scratch", "resnet18", "dinov2_vits14", "dinov2_vitb14", "dinov2_vitl14"],
                    default="scratch",
                    help="encoder: from-scratch UNet, a pretrained ImageNet ResNet-18, or a FROZEN DINOv2 foundation "
                         "backbone (vits/vitb/vitl) with a DPT-style decoder (lingbot-class features; fits 8 GB frozen)")
    ap.add_argument("--pose_head", choices=["siamese", "corr"], default="siamese",
                    help="pose front-end: global-pooled Siamese MLP, or a local correlation cost volume (better pose)")
    ap.add_argument("--smoke", action="store_true", help="1 tiny step on CPU/GPU, no checkpoint")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"
    dtype = torch.bfloat16 if (use_cuda and torch.cuda.get_device_capability()[0] >= 8) else torch.float32
    seqs = list_sequences()
    if not seqs:
        raise SystemExit("no TUM sequences under LIDAR3D_DATA_ROOT/train/tum-rgbd (download them first)")
    # pin the held-out sequence to long_office when present (keeps OWN_tum_office truly held-out + ATE comparable
    # across runs); otherwise fall back to the last sequence.
    val_seq = next((s for s in seqs if "long_office" in s), seqs[-1])
    train_seqs = [s for s in seqs if s != val_seq] or seqs
    if args.seqs:                                   # keep only the requested train subset (reproduce a specific config)
        wanted = [w.strip() for w in args.seqs.split(",") if w.strip()]
        train_seqs = [s for s in train_seqs if any(w in s for w in wanted)] or train_seqs
    mp = args.max_pairs if not args.smoke else 4
    datasets: list = [TUMPairs(s, image_size=args.size, max_pairs=mp) for s in train_seqs]
    if args.use_icl:
        datasets += [ICLPairs(s, image_size=args.size, max_pairs=mp) for s in icl_sequences()]
    if args.use_tartan:
        datasets += [TartanGroundPairs(s, image_size=args.size, max_pairs=mp) for s in tartanground_sequences()]
    train = ConcatDataset(datasets)
    dl = DataLoader(train, batch_size=(2 if args.smoke else args.batch), shuffle=True, num_workers=0, drop_last=True)

    model = OwnDepthPose(base=args.base, max_depth=10.0, backbone=args.backbone,
                         pose_head=args.pose_head).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, args.epochs * max(1, len(dl))))
    print(f"device={device} dtype={dtype} train_pairs={len(train)} val={os.path.basename(val_seq)} "
          f"params={sum(p.numel() for p in model.parameters())/1e6:.2f}M")

    steps = 0
    best_ate = float("inf")
    out_dir = Path(os.environ.get("LIDAR3D_MODELS_ROOT", "models")) / "own-depthpose"
    out_dir.mkdir(parents=True, exist_ok=True)
    import datetime as _dt
    run_id = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")   # unique per run so a run NEVER clobbers another's best
    for ep in range(1 if args.smoke else args.epochs):
        model.train()
        for b in dl:
            r0 = b["rgb0"].to(device)
            r1 = b["rgb1"].to(device)
            d0 = b["depth0"].to(device)
            rel = b["rel_pose"].to(device)
            Kb = b["K"].to(device)
            with torch.autocast("cuda", dtype=dtype, enabled=use_cuda):
                out = model(r0, r1)
                ld = depth_loss(out["depth0"].float(), out["logvar0"].float(), d0, 10.0)
                lp = pose_loss(out["rel_pose"].float(), rel)
                loss = ld + lp
                if args.photo_w > 0:
                    loss = loss + args.photo_w * photometric_loss(
                        r0.float(), r1.float(), out["depth0"].float(), out["rel_pose"].float(), Kb)
                if args.smooth_w > 0:
                    loss = loss + args.smooth_w * smoothness_loss(out["depth0"].float(), r0.float())
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            if not args.smoke:
                sched.step()
            steps += 1
            if steps % 20 == 0 or args.smoke:
                print(f"ep{ep} step{steps} loss={loss.item():.4f} depth={ld.item():.4f} pose={lp.item():.4f}")
            if args.smoke and steps >= 1:
                break
        if args.smoke:
            break
        ate = evaluate(model, val_seq, device, args.size, max_pairs=300)
        improved = ate < best_ate
        print(f"[epoch {ep}] val ATE={ate:.4f} m" + (" (best, saved)" if improved else ""))
        n_params = sum(p.numel() for p in model.parameters())
        _log_experiment(out_dir, {                     # append every epoch so NO experiment is ever lost
            "backbone": args.backbone, "pose_head": args.pose_head, "epoch": ep, "val_ate": round(ate, 4),
            "best_ate": round(min(ate, best_ate), 4),
            "is_best": improved, "params_M": round(n_params / 1e6, 3), "base": args.base, "size": args.size,
            "lr": args.lr, "use_icl": args.use_icl, "train_pairs": len(train), "val_seq": os.path.basename(val_seq),
        })
        if improved:                                   # EARLY STOPPING: keep the BEST checkpoint, not the last
            best_ate = ate
            ckpt = {"model": model.state_dict(), "max_depth": 10.0, "size": args.size, "base": args.base,
                    "backbone": args.backbone, "pose_head": args.pose_head, "val_ate": ate}
            tag = f"{args.backbone}-{args.pose_head}" if args.pose_head != "siamese" else args.backbone
            torch.save(ckpt, out_dir / f"own-depthpose-{tag}-{run_id}.pt")    # UNIQUE per-run archive (never clobbered)
            torch.save(ckpt, out_dir / "own-depthpose.pt")                    # canonical file the engine loads
            import json as _json
            (out_dir / "own-depthpose.meta.json").write_text(_json.dumps({    # small sidecar for accurate engine labels
                "backbone": args.backbone, "pose_head": args.pose_head, "val_ate": round(ate, 4),
                "size": args.size, "base": args.base, "use_icl": args.use_icl}))

    if args.smoke:
        print("SMOKE OK")
        return
    print(f"best val ATE={best_ate:.4f} m -> {out_dir / 'own-depthpose.pt'}")


if __name__ == "__main__":
    main()
