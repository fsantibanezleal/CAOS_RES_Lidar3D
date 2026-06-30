"""Headless test: does LingbotEngine.stream() yield sensible per-frame geometry live?"""
import sys, glob, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engines.lingbot import LingbotEngine
from app.config import EXAMPLES_DIR

paths = sorted(glob.glob(str(EXAMPLES_DIR / "oxford" / "*.png")))[:20]
print(f"{len(paths)} frames")
eng = LingbotEngine()
print("warmup..."); t = time.time(); eng.warmup(); print(f"  warmup {time.time()-t:.1f}s on {eng.device} dtype={eng.dtype}")

n = 0; first_pts = None
for fp in eng.stream(paths, {"max_frames": 20, "decimation": 8}):
    cam = fp.pose_c2w[3], fp.pose_c2w[7], fp.pose_c2w[11]
    print(f"  frame {fp.idx:2d}/{fp.total} kf={fp.is_keyframe!s:5s} "
          f"pts={fp.n_points:5d} cam=({cam[0]:+.2f},{cam[1]:+.2f},{cam[2]:+.2f}) "
          f"conf={fp.conf_mean:.2f} fps={fp.fps:.2f} vram={fp.vram_gb:.1f}GB "
          f"depth_png={'ok' if fp.depth_png.startswith('data:image') else 'NO'}")
    if first_pts is None:
        first_pts = fp.n_points
    n += 1
print(f"OK: streamed {n} frames, first-frame points={first_pts}")
assert n == 20, "expected 20 frames"
assert first_pts and first_pts > 100, "too few points"
print("ENGINE_TEST_OK")
