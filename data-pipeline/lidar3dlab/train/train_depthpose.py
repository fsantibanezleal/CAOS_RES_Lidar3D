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
from .dataset_tum import TUMPairs, list_sequences


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--size", type=int, default=224)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--max_pairs", type=int, default=None, help="cap pairs per sequence (smoke test)")
    ap.add_argument("--photo_w", type=float, default=0.0, help="self-supervised photometric loss weight (0=off)")
    ap.add_argument("--smoke", action="store_true", help="1 tiny step on CPU/GPU, no checkpoint")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_cuda = device.type == "cuda"
    dtype = torch.bfloat16 if (use_cuda and torch.cuda.get_device_capability()[0] >= 8) else torch.float32
    seqs = list_sequences()
    if not seqs:
        raise SystemExit("no TUM sequences under LIDAR3D_DATA_ROOT/train/tum-rgbd (download them first)")
    val_seq = seqs[-1]
    train_seqs = seqs[:-1] or seqs
    mp = args.max_pairs if not args.smoke else 4
    train = ConcatDataset([TUMPairs(s, image_size=args.size, max_pairs=mp) for s in train_seqs])
    dl = DataLoader(train, batch_size=(2 if args.smoke else args.batch), shuffle=True, num_workers=0, drop_last=True)

    model = OwnDepthPose(max_depth=10.0).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    print(f"device={device} dtype={dtype} train_pairs={len(train)} val={os.path.basename(val_seq)} "
          f"params={sum(p.numel() for p in model.parameters())/1e6:.2f}M")

    steps = 0
    best_ate = float("inf")
    out_dir = Path(os.environ.get("LIDAR3D_MODELS_ROOT", "models")) / "own-depthpose"
    out_dir.mkdir(parents=True, exist_ok=True)
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
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
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
        if improved:                                   # EARLY STOPPING: keep the BEST checkpoint, not the last
            best_ate = ate
            torch.save({"model": model.state_dict(), "max_depth": 10.0, "size": args.size, "val_ate": ate},
                       out_dir / "own-depthpose.pt")

    if args.smoke:
        print("SMOKE OK")
        return
    print(f"best val ATE={best_ate:.4f} m -> {out_dir / 'own-depthpose.pt'}")


if __name__ == "__main__":
    main()
