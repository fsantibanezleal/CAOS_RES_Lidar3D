"""TUM RGB-D loader for training OUR own depth+pose model. Real data (RGB + registered metric depth + a
ground-truth camera trajectory), downloaded to LIDAR3D_DATA_ROOT/train/tum-rgbd/<seq>/.

TUM format: rgb.txt / depth.txt = "timestamp filename"; groundtruth.txt = "timestamp tx ty tz qx qy qz qw"
(camera-to-world). Depth PNG is uint16, metric depth = value / 5000. Frames are associated by nearest
timestamp. Yields consecutive pairs (frame t, t+1) so the model learns per-frame depth AND relative pose.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation
from torch.utils.data import Dataset

# fr1 / fr2 / fr3 pinhole intrinsics (registered RGB frame), from the TUM RGB-D benchmark.
_INTR = {
    "freiburg1": (517.306, 516.469, 318.643, 255.314),
    "freiburg2": (520.909, 521.007, 325.141, 249.701),
    "freiburg3": (535.4, 539.2, 320.1, 247.6),
}


def _read_list(p: Path) -> list[tuple[float, str]]:
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        ts, fn = line.split()[:2]
        out.append((float(ts), fn))
    return out


def _read_gt(p: Path) -> tuple[np.ndarray, np.ndarray]:
    ts, poses = [], []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        v = [float(x) for x in line.split()]
        ts.append(v[0])
        c2w = np.eye(4)
        c2w[:3, :3] = Rotation.from_quat(v[4:8]).as_matrix()  # qx,qy,qz,qw
        c2w[:3, 3] = v[1:4]
        poses.append(c2w)
    return np.asarray(ts), np.asarray(poses)


def _nearest(ts: np.ndarray, t: float) -> int:
    return int(np.argmin(np.abs(ts - t)))


def _intr_for(seq_dir: str) -> tuple[float, float, float, float]:
    name = os.path.basename(seq_dir.rstrip("/\\"))
    for k, v in _INTR.items():
        if k in name:
            return v
    return _INTR["freiburg1"]


class TUMPairs(Dataset):
    """Consecutive RGB-D pairs with ground-truth relative pose, for supervised depth+pose training."""

    def __init__(self, seq_dir: str, image_size: int = 224, stride: int = 1, max_pairs: int | None = None,
                 max_gt_dt: float = 0.02):
        self.seq_dir = Path(seq_dir)
        self.size = image_size
        rgb = _read_list(self.seq_dir / "rgb.txt")
        depth = _read_list(self.seq_dir / "depth.txt")
        gts, gposes = _read_gt(self.seq_dir / "groundtruth.txt")
        d_ts = np.asarray([t for t, _ in depth])
        fx, fy, cx, cy = _intr_for(str(self.seq_dir))

        self.samples = []
        frames = []
        for t, fn in rgb:
            di = _nearest(d_ts, t)
            gi = _nearest(gts, t)
            if abs(d_ts[di] - t) > 0.02 or abs(gts[gi] - t) > max_gt_dt:
                continue
            frames.append((fn, depth[di][1], gposes[gi]))
        K0 = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], np.float64)
        # store base image size once (assume constant 640x480 for TUM)
        self.K0, self.W0, self.H0 = K0, 640, 480
        for i in range(0, len(frames) - stride, stride):
            self.samples.append((frames[i], frames[i + stride]))
        if max_pairs:
            self.samples = self.samples[:max_pairs]

    def _K(self) -> np.ndarray:
        s = self.size
        sx, sy = s / self.W0, s / self.H0
        K = self.K0.copy()
        K[0] *= sx
        K[1] *= sy
        return K.astype(np.float32)

    def _load_rgb(self, fn: str) -> np.ndarray:
        im = Image.open(self.seq_dir / fn).convert("RGB").resize((self.size, self.size), Image.BILINEAR)
        return (np.asarray(im, np.float32) / 255.0).transpose(2, 0, 1)  # [3,H,W]

    def _load_depth(self, fn: str) -> np.ndarray:
        im = Image.open(self.seq_dir / fn).resize((self.size, self.size), Image.NEAREST)
        return (np.asarray(im, np.float32) / 5000.0)  # [H,W] meters (0 = invalid)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, i: int) -> dict:
        (fn0, dfn0, c2w0), (fn1, _dfn1, c2w1) = self.samples[i]
        rel = np.linalg.inv(c2w0) @ c2w1              # frame t+1 expressed in frame t (relative pose)
        return {
            "rgb0": self._load_rgb(fn0), "rgb1": self._load_rgb(fn1),
            "depth0": self._load_depth(dfn0), "rel_pose": rel.astype(np.float32), "K": self._K(),
        }


_ICL_INTR = (481.20, 480.00, 319.50, 239.50)  # ICL-NUIM camera (fy positive-ified)


class ICLPairs(TUMPairs):
    """ICL-NUIM (synthetic, PERFECT ground-truth depth + pose). TUM-compatible: associations.txt pairs rgb<->depth
    by index, livingRoom*.gt.freiburg holds the GT poses (index tx ty tz qx qy qz qw), depth PNG scale 5000.
    Reuses TUMPairs' loaders + __getitem__; only the index build differs."""

    def __init__(self, seq_dir: str, image_size: int = 224, stride: int = 1, max_pairs: int | None = None):
        self.seq_dir = Path(seq_dir)
        self.size = image_size
        gt: dict[int, np.ndarray] = {}
        gtf = next(iter(self.seq_dir.glob("*.gt.freiburg")), None)
        if gtf:
            for line in gtf.read_text().splitlines():
                if not line.strip() or line.startswith("#"):
                    continue
                v = [float(x) for x in line.split()]
                c2w = np.eye(4)
                c2w[:3, :3] = Rotation.from_quat(v[4:8]).as_matrix()
                c2w[:3, 3] = v[1:4]
                gt[int(v[0])] = c2w
        frames = []
        for line in (self.seq_dir / "associations.txt").read_text().splitlines():
            p = line.split()
            if len(p) < 4:
                continue
            idx = int(p[0])
            if idx in gt:
                frames.append((p[3], p[1], gt[idx]))       # (rgb_fn, depth_fn, c2w)
        fx, fy, cx, cy = _ICL_INTR
        self.K0 = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], np.float64)
        self.W0, self.H0 = 640, 480
        self.samples = [(frames[i], frames[i + stride]) for i in range(0, len(frames) - stride, stride)]
        if max_pairs:
            self.samples = self.samples[:max_pairs]


def default_root() -> Path:
    return Path(os.environ.get("LIDAR3D_DATA_ROOT", "data/raw")) / "train" / "tum-rgbd"


def list_sequences() -> list[str]:
    root = default_root()
    return sorted(str(p) for p in root.glob("rgbd_dataset_*") if (p / "rgb.txt").exists())


def icl_sequences() -> list[str]:
    """ICL-NUIM sequences (a folder with associations.txt + a *.gt.freiburg)."""
    root = Path(os.environ.get("LIDAR3D_DATA_ROOT", "data/raw")) / "train" / "icl-nuim"
    return sorted(str(p.parent) for p in root.rglob("associations.txt"))


# TartanGround camera-optical <- NED body change of basis: optical (x-right, y-down, z-forward) axes expressed in
# the NED body frame (x-forward, y-right, z-down): opt_x->ned_y, opt_y->ned_z, opt_z->ned_x.
_NED_FROM_OPT = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], np.float64)


class TartanGroundPairs(Dataset):
    """TartanGround (TartanAir v2 ground-robot) pairs: RGB + PERFECT synthetic depth + pose, huge and diverse.
    Format per trajectory: image_<cam>/######_<cam>.png, depth_<cam>/######_<cam>_depth.png (RGBA bytes = a float32
    metric depth), pose_<cam>.txt (x y z qx qy qz qw, camera-to-world in NED). Cameras are 640x640, 90 deg FoV
    (fx=fy=320, cx=cy=320). Poses are converted NED->optical so they compose with our optical-frame depth; depths
    beyond `max_depth` (sky / far outdoor) are masked invalid so they do not corrupt an indoor-range model."""

    def __init__(self, seq_dir: str, image_size: int = 224, stride: int = 1, max_pairs: int | None = None,
                 camera: str = "lcam_front", max_depth: float = 10.0):
        self.seq_dir = Path(seq_dir)
        self.size = image_size
        self.max_depth = max_depth
        self.img_dir = self.seq_dir / f"image_{camera}"
        self.dep_dir = self.seq_dir / f"depth_{camera}"
        imgs = sorted(self.img_dir.glob(f"*_{camera}.png"))
        poses = np.loadtxt(self.seq_dir / f"pose_{camera}.txt").reshape(-1, 7)
        frames = []
        for i, ip in enumerate(imgs):
            if i >= len(poses):
                break
            dp = self.dep_dir / (ip.stem + "_depth.png")
            if not dp.exists():
                continue
            c2w = np.eye(4)
            c2w[:3, :3] = Rotation.from_quat(poses[i, 3:7]).as_matrix()
            c2w[:3, 3] = poses[i, :3]
            frames.append((str(ip), str(dp), c2w))
        fx = fy = 320.0 * (image_size / 640.0)
        cx = cy = 320.0 * (image_size / 640.0)
        self.K0 = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], np.float32)   # already at working res
        self.samples = [(frames[i], frames[i + stride]) for i in range(0, len(frames) - stride, stride)]
        if max_pairs:
            self.samples = self.samples[:max_pairs]

    def __len__(self) -> int:
        return len(self.samples)

    def _rgb(self, p: str) -> np.ndarray:
        im = Image.open(p).convert("RGB").resize((self.size, self.size), Image.BILINEAR)
        return (np.asarray(im, np.float32) / 255.0).transpose(2, 0, 1)

    def _depth(self, p: str) -> np.ndarray:
        rgba = np.asarray(Image.open(p))                       # (H,W,4) uint8; the 4 bytes ARE a float32 metre depth
        d = np.ascontiguousarray(rgba).view(np.float32).squeeze(-1)
        d = np.array(Image.fromarray(d).resize((self.size, self.size), Image.NEAREST), np.float32)
        d[d >= self.max_depth] = 0.0                           # mask sky/far so an indoor-range model is not corrupted
        return d

    def __getitem__(self, i: int) -> dict:
        (ip0, dp0, c2w0), (ip1, _dp1, c2w1) = self.samples[i]
        rel_ned = np.linalg.inv(c2w0) @ c2w1                   # relative pose, NED frame
        p = np.eye(4)
        p[:3, :3] = _NED_FROM_OPT
        rel = (p.T @ rel_ned @ p).astype(np.float32)           # -> optical frame (matches our depth unprojection)
        return {"rgb0": self._rgb(ip0), "rgb1": self._rgb(ip1),
                "depth0": self._depth(dp0), "rel_pose": rel, "K": self.K0.copy()}


def tartanground_sequences() -> list[str]:
    """TartanGround trajectory folders (a dir holding image_<cam>/, depth_<cam>/ and pose_<cam>.txt)."""
    root = Path(os.environ.get("LIDAR3D_DATA_ROOT", "data/raw")) / "train" / "tartanground"
    return sorted(str(p.parent) for p in root.rglob("pose_lcam_front.txt"))
