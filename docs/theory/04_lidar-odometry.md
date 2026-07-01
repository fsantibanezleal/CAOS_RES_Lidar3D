# 04 · LiDAR odometry: point-to-plane ICP, drift, and KISS-ICP

The second modality. The camera engine ([02](02_geometric-context-transformer.md)) reconstructs
LiDAR-*like* clouds from video; this engine consumes **actual LiDAR scans** and estimates the trajectory by
registering consecutive scans. It is what makes the name "Lidar 3D" honest. This page gives the geometry of
point-to-plane ICP, the linearized normal equations, the scan-to-scan odometry chain and its drift, why
KISS-ICP is the pinned SOTA option, and how camera vs LiDAR modalities compare. Code: `data-pipeline/
lidar3dlab/model/lidar.py`; survey: `docs/research/lidar-slam-and-perception.md`.

---

## 1. The problem

A LiDAR emits, at each time $i$, a **scan**: an unordered set of 3D points $S_i = \{p^{(i)}_j\} \subset
\mathbb{R}^3$ in the sensor frame (KITTI Velodyne: `.bin` of $[x,y,z,\text{intensity}]$ floats,
`lidar.py:_real_scans`). There are no pixels and no intrinsics; the geometry is measured directly. The task
is **odometry**: recover the sensor pose $\hat P_i \in SE(3)$ at each scan and, by transforming every scan
into a common frame, build a registered map. Unlike the monocular camera, LiDAR is **metric by construction**
(ranges are real metres), so there is no scale ambiguity to resolve.

## 2. Registration: aligning two point clouds

The core operation is **registration**: find the rigid transform $T \in SE(3)$ that best aligns a source
cloud $\mathcal{P}$ (scan $i$) onto a target cloud $\mathcal{Q}$ (scan $i-1$). "Best" is a least-squares fit
over point correspondences. Two residual choices define the ICP variant:

- **Point-to-point ICP**: minimize distance between corresponding points,
  $\sum_j \lVert T p_j - q_j \rVert_2^2$.
- **Point-to-plane ICP** (used here, `TransformationEstimationPointToPlane`): minimize the distance from the
  transformed source point to the **tangent plane** of the target at its match, using the target surface
  normal $n_j$.

Point-to-plane converges faster and is more accurate on the piecewise-planar surfaces typical of real scenes
(walls, ground, facades) because it lets points slide **along** the surface and only penalizes motion
**across** it. That is why the lab's engine and KISS-ICP both use a point-to-plane (or the closely related
symmetric/GICP) residual.

## 3. The point-to-plane objective and its normal equations

Let $\{(p_j, q_j, n_j)\}$ be the current correspondences: $p_j$ a source point, $q_j$ its nearest target
point, $n_j$ the unit normal of the target surface at $q_j$. The point-to-plane cost for a candidate
transform $T$ is

$$
E(T) \;=\; \sum_j \Big(\big(T p_j - q_j\big)\cdot n_j\Big)^2 .
$$

$SE(3)$ is nonlinear, so ICP linearizes around the current estimate. For a small motion write the rigid
transform as a rotation $R \approx I + [\,\omega\,]_\times$ (with $\omega = (\alpha,\beta,\gamma)$ the
small-angle vector, $[\cdot]_\times$ the skew-symmetric matrix) and a translation $\mathbf{t}$. Then

$$
T p_j \approx p_j + \omega \times p_j + \mathbf{t},
$$

and each residual becomes **linear** in the 6-vector $\xi = (\omega, \mathbf{t}) \in \mathbb{R}^6$:

$$
r_j(\xi) = \big((p_j - q_j) + \omega\times p_j + \mathbf{t}\big)\cdot n_j
         = \underbrace{\big[(p_j\times n_j)^\top \;\; n_j^\top\big]}_{a_j^\top}\,\xi \;+\; \underbrace{(p_j - q_j)\cdot n_j}_{b_j}.
$$

Stacking rows $a_j^\top$ into $A$ and $-b_j$ into $\mathbf{b}$, the least-squares step solves the $6\times6$
**normal equations**

$$
\big(A^\top A\big)\,\xi^\star = A^\top \mathbf{b}, \qquad
A^\top A = \sum_j a_j a_j^\top,\quad A^\top\mathbf{b} = -\sum_j a_j b_j ,
$$

then updates $T \leftarrow \exp(\xi^\star)\,T$ (apply the incremental rotation/translation), re-associates
correspondences by nearest neighbor, and iterates until convergence. The lab caps this at
`max_iteration=30` with a `max_correspondence_distance = voxel*2.5` gate so far-apart (spurious) matches do
not enter the sum (`lidar.py:_icp`). The $6\times6$ system is tiny, which is why ICP runs real-time on a CPU.

## 4. Preprocessing that makes it work

Raw scans are dense and noisy; three standard steps precede the solve (`lidar.py:_icp`):

1. **Voxel downsampling** (`voxel_down_sample(0.18)`): one representative point per 18 cm voxel. Uniformizes
   density (near surfaces are over-sampled) and cuts the correspondence search cost.
2. **Normal estimation** (`estimate_normals`, hybrid KD-tree, `radius = voxel*3`, `max_nn=20`): fits a local
   plane per target point to get $n_j$; required by the point-to-plane residual.
3. **Correspondence gating** (`max_correspondence_distance = voxel*2.5`): rejects matches beyond a radius so
   outliers and non-overlapping regions are ignored.

## 5. Scan-to-scan odometry and drift

The engine chains **scan-to-scan** registrations into a trajectory (`lidar.py:reconstruct`):

```python
poses = [I4]
for i in 1..N-1:
    rel = icp(scan_i, scan_{i-1}, init=I4, voxel)   # register scan_i onto scan_{i-1}
    poses.append(poses[-1] @ rel)                    # compose into world
```

so the world pose is a running product of relative transforms,

$$
\hat P_i = \prod_{\tau=1}^{i} \Delta \hat P_\tau, \qquad \Delta\hat P_\tau = \text{ICP}(S_\tau, S_{\tau-1}).
$$

Each registered scan is transformed into the world frame ($w = \text{scan}\,R^\top + t$), decimated, and
accumulated into a height-colored map; the camera centers form the odometry trajectory. This is the same
compounding structure as [01 §3.2](01_streaming-reconstruction.md#32-temporal-consistency): every relative
step carries a small error $\epsilon_\tau$, and because the pose is a product,

$$
\hat P_i = \Big(\textstyle\prod_\tau \Delta P^\star_\tau\Big)\cdot \exp\!\Big(\textstyle\sum_\tau \tilde\epsilon_\tau\Big) \text{ (to first order)},
$$

the errors **accumulate** and the estimate **drifts** away from truth over a long run, even when each step is
individually good. Scan-to-scan has no memory beyond the previous frame, so it is the most drift-prone
variant. Real systems mitigate drift by **scan-to-map** registration (align to the accumulated map, not just
the last scan), a **local map** window, and **loop closure** (recognize a revisited place and add a
pose-graph constraint). The lab's synthetic engine is deliberately scan-to-scan to expose drift as a visible
phenomenon; the production path is a KISS-ICP swap (§7) that adds the local-map machinery.

## 6. The synthetic LiDAR case (CI-safe)

`LID_synthetic` builds scans procedurally so the pipeline, contracts, and web replay are exercised with **no
dataset and no GPU** (`lidar.py:_synthetic_scans`): a corridor world cloud (two walls, floor, ceiling) is
generated, a forward-moving ground-truth path is defined, and each pose "sees" a range-limited, subsampled,
noisy slice of the world in the sensor frame. ICP then recovers a ~9 m path and a height-colored registered
map. Because a ground-truth path exists here, this case is also where ATE can be computed honestly (the real
example sequences carry no GT; `stages/evaluate.py` reports "no GT" rather than faking it).

## 7. Why KISS-ICP is the SOTA option

The lab's `_icp` is a correct, standard Open3D point-to-plane registration, deliberately simple and swappable
behind one interface (`lidar.py` docstring). The pinned production upgrade is **KISS-ICP** (RA-L 2023,
PRBonn, MIT, `pip install kiss-icp`; `docs/research/lidar-slam-and-perception.md` §2.1). KISS-ICP is the
modern reference for **pure-LiDAR, IMU-free, ROS-optional, CPU-real-time** odometry, and it is "point-to-point
ICP done carefully": its accuracy comes not from a fancy residual but from a disciplined pipeline:

- **Adaptive correspondence threshold** derived from the data (no per-dataset tuning, "no knobs"),
- **Constant-velocity motion model** to deskew the scan and initialize each registration,
- **Robust kernel + local map** (voxel hash) so it registers **scan-to-map**, not just scan-to-scan, which
  substantially reduces drift versus §5.

Its sibling **KISS-SLAM** (IROS 2025) adds `MapClosures` loop closure + a g2o pose graph, i.e. it supplies
exactly the loop-closure back-end lingbot-map lacks, on the LiDAR side. **MAD-ICP** (RA-L 2024, BSD-3) is the
other strong CPU-only contender (kd-tree surfel map). All three are permissive and pip-installable, which is
why they are the realistic engines for a Python + browser research repo. To swap: implement the same
`(scans, seed)` to `poses` step behind `lidar.reconstruct` and pin the package (see
[guide 07](../guides/07_lidar-modality.md)).

## 8. Camera vs LiDAR modalities

| Axis | Camera engine (lingbot-map) | LiDAR engine (ICP / KISS-ICP) |
|---|---|---|
| Input | ordered RGB frames, intrinsics-free | unordered 3D scans (`.bin`/`.npy`/`.ply`/`.pcd`) |
| Geometry source | **learned** regression (feed-forward prior) | **measured** ranges + geometric registration |
| Scale | ambiguous, fixed by anchor $s$ ([03 §5](03_pointmaps-and-geometry.md)) | **metric by construction** |
| Per-frame output | pose + dense depth + confidence | pose (relative, composed) + registered points |
| Color | true RGB from frames | height-colored (no photometric channel unless fused) |
| Compute | GPU (~1B ViT), ~20 FPS with paged cache | CPU real-time, tiny $6\times6$ solve |
| Drift control | trajectory memory (no loop closure) | local map / loop closure (in KISS-SLAM) |
| Lighting / texture | needs texture + light; fails on blank walls | independent of lighting and texture |
| Failure modes | textureless / dynamic / distribution shift | featureless corridors (slip along axis), moving objects |

The two are complementary, which is the premise of the lab's cross-modal work: LiDAR gives a metric,
lighting-invariant trajectory that can **teach** the camera engine (distillation, [06 D2](06_novel-agenda.md)),
and the camera gives dense photometric texture the LiDAR lacks. The pipeline dispatches by
`SequenceSpec.modality` (`"camera"` vs `"lidar"`) in `stages/infer.py`, so both live behind the identical
contract and export path.
