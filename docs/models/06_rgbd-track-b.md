# Track B: RGB + sensor depth (the two-track model family)

The lab's models now form two explicit tracks, set by the product decision that both must exist:

| Track | Input | Metric scale | Engines | Where it stands |
|---|---|---|---|---|
| **A: RGB-only** | one ordinary camera | must be inferred (the hard part) | Estela (ours, trained), lingbot-map (SOTA pointmap reference) | Estela 0.28 m deployed; the measured ceiling is ~0.02 m, blocked ONLY by monocular metric scale |
| **B: RGB + depth sensor** | camera + Kinect/LiDAR-class depth | measured by the sensor (free) | `rgbd-sensor` (this page) | 0.034-0.098 m across TUM scenes, no scale ambiguity |

Code: `data-pipeline/lidar3dlab/model/rgbd_engine.py`, registered as `rgbd-sensor` in the model-agnostic registry.

## Why Track B exists (what a depth sensor buys)

The whole 2026-07-04 experiment campaign (see [model history](02_model-history.md) and the improvement action plan
in the management repo) converged on one fact: with a good metric depth, a classical geometric pose is
~10x better than the deployed RGB-only trajectory, and the ONLY blocker in RGB-only mode is the absolute metric
scale, which monocular vision fundamentally cannot observe (jerk and reprojection objectives are degenerate in
scale; a learned model's scale prior drifts per scene). A depth sensor measures that scale directly. Track B is
therefore not a luxury: it is the configuration where the measured ~10x ceiling is reachable TODAY.

## Method (classical, transparent, honest)

Per RGB pair (consecutive AND skip, see the fusion below):

1. **Match** SIFT keypoints on the RGB frames (Lowe ratio 0.75).
2. **Back-project** the frame-i matches to 3D camera-frame points with the SENSOR depth (metric metres; sensor
   holes, depth 0, and far returns beyond 8 m are discarded, never inpainted).
3. **Solve** the relative pose with PnP + RANSAC (frame-i 3D points against their frame-j pixels, reprojection
   threshold 3 px), giving $T_{i\to j}$ and the RANSAC inlier count (the edge's confidence).
4. **Fuse the trajectory with the windowed pose-graph** (Estela-W's `window_pgo`, run forward-only): overlapping
   6-frame windows, edges = 5 consecutive + 4 skip-2, per-edge weight = the PnP inlier count, composed window to
   window by the shared frame. This is the M-C solve in production: over these STRONG metric edges it measurably
   cuts drift (7 to 26% on the validation scenes; over weak monocular edges it fails, the P0.1 finding), which is
   exactly what the M-C synthetic self-test predicted. Falls back to the plain consecutive chain without torch.
5. **Fuse the cloud**: unproject every frame's sensor depth at its solved pose. What the sensor did not measure is
   absent from the cloud; nothing is hallucinated.

If a pair has too few valid matches (rare: zero occurrences across the validation scenes), the pose HOLDS rather
than inventing motion, and the event is counted.

## Validation (2026-07-04, before the engine was written)

The method was validated standalone against ground truth before productization (umeyama ATE, metres), first as a
plain consecutive chain, then with the windowed pose-graph fusion (the shipped configuration):

| sequence | RGB-only Estela (deployed) | Track B chain | **Track B + window fusion (shipped)** |
|---|---|---|---|
| freiburg3_long_office (300) | 0.281 | 0.097 | **0.085** (-13%) |
| freiburg1_desk (120) | 0.119 | 0.036 | **0.034** (-7%) |
| freiburg2_pioneer (150) | 0.031 | 0.033 | **0.024** (-26%) |

Zero fallback pairs on all three. This is also the first PRODUCTION use of the M-C differentiable windowed
pose-graph: it fails over weak monocular edges (the P0.1 finding) but pays off over these strong metric edges,
exactly as its synthetic self-test predicted. The residual error on `long_office` at range reflects Kinect depth
noise and holes; a confidence-weighted fusion of sensor depth with a foundation model's depth SHAPE (Depth
Anything V2) is the tracked refinement.

## The cases

`RGBD_tum_office` and `RGBD_tum_desk` bake the SAME scenes as `OWN_tum_office` / `OWN_tum_desk`, so the App shows
an honest side-by-side: same frames, same intrinsics, RGB-only vs RGB+depth. The per-frame panel shows the real
sensor depth (with its holes) next to the RGB stream.

## Honest limitations

- Track B needs the depth stream: it applies to RGB-D/LiDAR captures, not to plain video. That is Track A's job.
- The pose is frame-to-frame (no loop closure); on very long sequences drift will accumulate, and the windowed
  fusion (Estela-W's `window_pgo`) over these strong metric edges is the natural extension.
- Kinect-class sensors fail on dark/specular/far surfaces; those regions are honestly missing from the cloud.
