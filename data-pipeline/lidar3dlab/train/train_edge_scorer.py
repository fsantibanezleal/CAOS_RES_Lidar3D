"""E4: train the tiny edge scorer on the labeled edge dataset and export the checkpoint.

Validation is a HELD-OUT TRAINING sequence (structure_texture_far by default), never one of the
I1 five: the scorer's own generalization is scored here (Spearman rank correlation between
predicted and true edge error: ranking is what the PGO weighting consumes), but the SHIP
decision belongs exclusively to the end-to-end A/B (eval_edge_scorer). Alpha (the weight-mapping
temperature) is calibrated on the validation split: alpha = 1 / p75(true err), so a
75th-percentile-bad edge gets weight ~exp(-1) = 0.37.

    PYTHONPATH=data-pipeline python -m lidar3dlab.train.train_edge_scorer
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from ..model.edge_scorer import N_FEAT, build_net, save_scorer, scorer_path


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = np.sqrt((ra**2).sum() * (rb**2).sum())
    return float((ra * rb).sum() / denom) if denom > 0 else 0.0


def main() -> None:
    import torch

    ap = argparse.ArgumentParser()
    ap.add_argument("--edges", default="data/derived/e4-edges")
    ap.add_argument("--val_seq", default="structure_texture_far", help="substring of the scorer-val sequence")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--seed", type=int, default=4)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    files = sorted(Path(args.edges).glob("*.npz"))
    if not files:
        raise SystemExit(f"no edge files under {args.edges}; run edge_dataset first")
    train_f, train_l, val_f, val_l = [], [], [], []
    for f in files:
        d = np.load(f)
        if len(d["labels"]) == 0:
            continue
        (val_f if args.val_seq in f.name else train_f).append(d["feats"])
        (val_l if args.val_seq in f.name else train_l).append(d["labels"])
    X = np.concatenate(train_f)
    y = np.concatenate(train_l)
    Xv = np.concatenate(val_f) if val_f else np.zeros((0, N_FEAT), np.float32)
    yv = np.concatenate(val_l) if val_l else np.zeros((0,), np.float32)
    if len(Xv) == 0:
        raise SystemExit(f"validation sequence '{args.val_seq}' contributed no edges; pick another")
    print(f"train edges {len(y)} (from {len(train_f)} seqs), val edges {len(yv)}")

    mean = X.mean(0)
    std = X.std(0) + 1e-6
    net = build_net()
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    xt = torch.from_numpy((X - mean) / std)
    yt = torch.from_numpy(y)[:, None]
    xv = torch.from_numpy((Xv - mean) / std)

    for epoch in range(args.epochs):
        opt.zero_grad()
        loss = torch.nn.functional.smooth_l1_loss(net(xt), yt)
        loss.backward()
        opt.step()
        if (epoch + 1) % 100 == 0:
            with torch.no_grad():
                pv = net(xv).numpy()[:, 0]
            print(f"epoch {epoch + 1}: train loss {float(loss):.4f}, val spearman {_spearman(pv, yv):.3f}")

    with torch.no_grad():
        pv = net(xv).numpy()[:, 0]
        pt = net(xt).numpy()[:, 0]
    rho_val = _spearman(pv, yv)
    rho_train = _spearman(pt, y)
    # Baseline the ranking against the pre-E4 heuristic: the (negated) inlier count, feature 3.
    rho_inliers = _spearman(-Xv[:, 3], yv)
    alpha = float(1.0 / max(np.percentile(np.expm1(yv), 75), 1e-3))
    report = {
        "train_edges": int(len(y)), "val_edges": int(len(yv)), "val_seq": args.val_seq,
        "spearman_val": rho_val, "spearman_train": rho_train,
        "spearman_neg_inliers_baseline": rho_inliers, "alpha": alpha, "seed": args.seed,
    }
    print(f"scorer val spearman {rho_val:.3f} vs -inliers baseline {rho_inliers:.3f}; alpha {alpha:.3f}")
    out = scorer_path()
    save_scorer(out, net, mean, std, alpha, report)
    print(f"exported -> {out}")


if __name__ == "__main__":
    main()
