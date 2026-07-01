# 03 · Pointmaps, pose encoding, and the depth-to-world geometry

Where [02](02_geometric-context-transformer.md) produced per-frame outputs (`pose_enc`, dense metric depth,
confidence), this page turns them into a metric, colored world point cloud, and explains every geometric
object involved: pointmaps, the `absT_quaR_FoV` pose encoding, the camera-to-world transform, the
depth-to-world unprojection (the load-bearing equation of the lab), intrinsics self-calibration, and
confidence filtering. Code references are to `data-pipeline/lidar3dlab/model/geometry.py`,
`.../model/lingbot.py`, and `third_party/lingbot-map/lingbot_map/utils/pose_enc.py`.

---

## 1. Pointmaps: the representation the lineage regresses

A **pointmap** is a dense map that assigns to every pixel $(u,v)$ a 3D point $X(u,v) \in \mathbb{R}^3$ in a
common reference frame. It is the object DUSt3R introduced and the whole feed-forward lineage regresses
([05](05_sota-lineage.md)): instead of predicting depth in the camera frame and separately a pose, a pointmap
directly ties pixels to world coordinates. Depth is the special case where the points are expressed in the
camera frame ($Z$ = depth); a pose then relates that to the world.

lingbot-map exposes both views: a depth head (metric depth per pixel, camera frame) and, optionally, a point
head (world points per pixel). The two are related by exactly the unprojection below. The lab reconstructs
the cloud from **depth + pose + intrinsics** because that keeps the geometry explicit and lets confidence
filtering happen on the depth confidence.

## 2. The pose encoding: `absT_quaR_FoV`

The camera head does not emit a raw $3\times4$ matrix; it emits a compact **9-D pose encoding** per frame
(`pose_enc` $\in \mathbb{R}^{S\times 9}$), the `absT_quaR_FoV` parameterization
(`lingbot_map/utils/pose_enc.py`):

$$
\text{pose\_enc} = [\; \underbrace{t_x, t_y, t_z}_{\text{abs. translation }T\ (3)}\; ,\; \underbrace{q_x, q_y, q_z, q_w}_{\text{rotation quaternion }q\ (4)}\; ,\; \underbrace{\mathrm{fov}_h, \mathrm{fov}_w}_{\text{field of view }(2)}\; ].
$$

Decoding (`pose_encoding_to_extri_intri`, `pose_encoding_type="absT_quaR_FoV"`):

- **Rotation.** $R = \mathrm{quat\_to\_mat}(q) \in SO(3)$.
- **Extrinsics.** $E = [\,R \mid T\,] \in \mathbb{R}^{3\times4}$, in the OpenCV convention (x-right, y-down,
  z-forward), representing the **world-to-camera** transform.
- **Intrinsics** (built from FoV, §5).

Why this encoding: a quaternion is a singularity-free 4-DOF rotation (vs Euler angles); absolute translation
plus quaternion is the minimal 7-DOF rigid pose; and encoding **field of view** rather than focal length in
pixels makes the intrinsics resolution-independent and lets the network **self-calibrate** (§5). The lab
never hand-supplies intrinsics; they come out of the pose encoding.

## 3. Extrinsics vs camera-to-world; the SE(3) inverse

The decoded extrinsics $E = [R \mid T]$ are **world-to-camera**: they map a world point $X_w$ into the camera
frame, $X_c = R\,X_w + T$. To place pixels into the world we need the inverse, the **camera-to-world** pose
$P_{c2w} = [R_{c2w} \mid t_{c2w}]$. For a rigid transform the inverse is closed-form (no matrix solve):

$$
R_{c2w} = R^\top, \qquad t_{c2w} = -R^\top T .
$$

The engine computes this with `closed_form_inverse_se3` / `closed_form_inverse_se3_general` after padding
$E$ to a $4\times4$ homogeneous matrix (`lingbot.py`: build `e4`, set bottom row $[0,0,0,1]$, invert, take
the top $3\times4$). The lab stores the result as a row-major 12-vector per frame
(`ReconResult.poses_c2w` shape $[S,12]$); the frame's **camera center** in world coordinates is exactly
$t_{c2w}$ (the last column), and the trajectory is the polyline through those centers
(`trajectory_length`, `geometry.py`).

## 4. The depth-to-world unprojection (the load-bearing equation)

Given, for frame $i$: dense depth $D(u,v)$, intrinsics $K$, camera-to-world $P_{c2w}=[R_{c2w}\mid t_{c2w}]$,
and RGB $(u,v)$, the world point at pixel $(u,v)$ is

$$
\boxed{\;
X_{\text{world}}(u,v) \;=\; R_{c2w}
\begin{bmatrix}
\dfrac{u - c_x}{f_x}\, D(u,v) \\[2mm]
\dfrac{v - c_y}{f_y}\, D(u,v) \\[1mm]
D(u,v)
\end{bmatrix}
\;+\; t_{c2w}
\;}
$$

with $K = \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix}$. This is the exact
computation in `unproject_depth` (`geometry.py`):

```python
x = (uu - cx) / fx * depth          # camera-frame X
y = (vv - cy) / fy * depth          # camera-frame Y
cam = np.stack([x, y, depth], -1)   # camera-frame point (Z = metric depth)
world = cam @ c2w[:3, :3].T + c2w[:3, 3]   # rotate into world, then translate by the camera center
```

Reading it in two steps:

1. **Backprojection (pixel, to camera ray, to 3D).** Inverting the pinhole projection: a pixel $(u,v)$ with
   metric depth $D$ is the camera-frame point
   $X_c = D\, K^{-1} [u, v, 1]^\top = \big(\tfrac{u-c_x}{f_x}D,\ \tfrac{v-c_y}{f_y}D,\ D\big)^\top$. The depth
   $D$ carries the **absolute scale** set by the anchor ([02 §4.1](02_geometric-context-transformer.md#41-anchor-context-coordinate-grounding-metric-scale)),
   so $X_c$ is in metres.
2. **Camera to world (rigid transform).** $X_{\text{world}} = R_{c2w} X_c + t_{c2w}$. Because every frame's
   $P_{c2w}$ shares one world frame, unprojecting all frames' depths lands them in a **single consistent
   metric cloud**; overlapping observations fuse.

The batched tensor version is `GCTBase._unproject_depth_to_world` (identical math via
`torch.einsum('bsij,bshwj->bshwi', c2w, camera_points_h)`); the lab uses the pure-NumPy
`unproject_depth` per frame so the synthetic CPU lane and the tests need no torch.

## 5. Intrinsics self-calibration (from field of view)

The camera head predicts **field of view**, not pixel focal lengths, so the model is self-calibrating: no
COLMAP, no intrinsics file. Intrinsics are reconstructed from FoV and the working resolution $(H,W)$
(`pose_encoding_to_extri_intri`, `build_intrinsics=True`):

$$
f_x = \frac{W/2}{\tan(\mathrm{fov}_w/2)}, \qquad
f_y = \frac{H/2}{\tan(\mathrm{fov}_h/2)}, \qquad
c_x = \frac{W}{2}, \qquad c_y = \frac{H}{2}.
$$

The principal point is assumed at the image center. This is the inverse of the encoding direction
(`extri_intri_to_pose_encoding`: $\mathrm{fov}_h = 2\arctan\!\big(\tfrac{H/2}{f_y}\big)$,
$\mathrm{fov}_w = 2\arctan\!\big(\tfrac{W/2}{f_x}\big)$). Encoding FoV instead of pixels makes the pose
representation independent of the exact crop/resolution the loader produced, which is what lets the same
weights ingest arbitrary footage.

Note on conventions: the model works in OpenCV pixel coordinates (top-left pixel center at $(0,0)$); a
COLMAP-sourced $K$ (top-left at $(0.5,0.5)$) must be shifted by $-0.5$ in $c_x, c_y$
(`colmap_to_opencv_intrinsics`), which matters only if you feed external intrinsics rather than using the
self-calibration.

## 6. Confidence filtering and fusion

The depth head also emits a per-pixel confidence $\hat C_i(u,v)$ (`depth_conf`). The lab drops the least
reliable pixels **before** fusion, per frame, with a **quantile** threshold so the fraction dropped is
controlled rather than an absolute cutoff (`lingbot.py`):

$$
\theta_i = Q_{\,q}\big(\hat C_i\big), \qquad \text{keep } (u,v) \iff \hat C_i(u,v) \ge \theta_i,
$$

with $q = $ `conf_quantile` (default 0.30, i.e. discard the lowest-confidence 30%). The kept points are also
finiteness-checked (`np.isfinite(world).all(1)` and a nonzero-norm guard) so NaN/inf depths never enter the
cloud. Fusion is a plain concatenation of every frame's kept, unprojected, colored points into one array
(`np.concatenate(all_p)`), with colors taken directly from the source RGB at each surviving pixel
(`rgb.reshape(-1,3) * 255`). The result is the metric, RGB-colored world cloud stored in `ReconResult.points`
/ `.colors`; the `refine` stage then optionally voxel-downsamples, removes statistical outliers, and
estimates normals (Open3D), which is the hook for a textured mesh
([guide 07](../guides/07_lidar-modality.md) and `stages/refine.py`).

## 7. Decimation and the committed artifact

For the public replay the raw cloud (up to millions of points; `oxford` bakes ~193k after decimation) is too
large to ship, so unprojection keeps **every $d$-th pixel** in each axis (`decimate` in `unproject_depth`;
`decimation` in the `SequenceSpec`, default 6). Decimation happens on the pixel grid **before** unprojection
so it is cheap and uniform in image space. The decimated colored cloud, the per-frame poses (12-vector each),
the trajectory length, the bounding box, and a few base64 depth thumbnails are what the export stage writes
into the committed trace (CONTRACT 2). The web app renders that cloud with three.js and draws the camera
frustums along the trajectory; the geometry it displays is exactly the equation of §4 evaluated offline.

## 8. Summary of objects

| Object | Symbol | Shape | Source | Frame |
|---|---|---|---|---|
| Pose encoding | `pose_enc` | $[S,9]$ | camera head | n/a |
| Extrinsics | $E=[R\mid T]$ | $[S,3,4]$ | decode `pose_enc` | world-to-camera |
| Camera-to-world | $P_{c2w}=[R_{c2w}\mid t_{c2w}]$ | $[S,3,4]$ | $SE(3)$ inverse of $E$ | camera-to-world |
| Intrinsics | $K$ | $[S,3,3]$ | FoV + $(H,W)$ | pixels |
| Depth | $D$ | $[S,H,W]$ | depth head | camera (metric) |
| Confidence | $\hat C$ | $[S,H,W]$ | depth head | n/a |
| World cloud | $X_{\text{world}}$ | $[P,3]$ | unproject + fuse | world (metric) |
| Colors | (RGB) | $[P,3]$ u8 | source RGB | n/a |

All of it is one metric world frame, grounded on the anchor scale $s$, produced feed-forward with no per-scene
optimization.
