# Estela: the own depth+pose model

**Estela** is our own, from-scratch, trainable model for streaming reconstruction from an ordered RGB stream. It
predicts, per frame, a dense metric depth with a learned confidence, and, per consecutive pair, a relative camera
pose. The inference engine (`model/own_engine.py`) accumulates the relative poses into a camera-to-world trajectory
and unprojects each frame's depth into a single fused, RGB-colored world point cloud with our tested geometry
(`model/geom.py`). No vendored reconstruction model is involved.

The name (Spanish for the wake a moving body leaves, and also a stele, a standing carved stone) captures what the
model produces: a moving camera's trajectory and the 3D structure it leaves behind. The multi-frame windowed
variant is [Estela-W (M-C)](05_windowed-pose-graph.md). The internal code symbol is still `OwnDepthPose`; a rename
to match the brand is a tracked follow-up.

Code: `data-pipeline/lidar3dlab/model/nets/own_depthpose.py`.

## Two interchangeable backbones

Both variants expose the identical forward signature `forward(rgb0, rgb1) -> {depth0, logvar0, xi, rel_pose}` and
are selected by `OwnDepthPose(backbone=...)`, so they are drop-in comparable and both are kept:

| Backbone | Encoder | Params | External weights | Intent |
|---|---|---|---|---|
| `scratch` | our UNet encoder (`DepthNet`) + a small pose convnet (`PoseNet`) | ~2.2 M | none | the honest *desde cero* baseline |
| `resnet18` | ImageNet **ResNet-18** shared by the depth decoder and a Siamese pose head | ~12.8 M | ImageNet backbone only | the quality-oriented variant: sharper, more consistent depth and steadier pose |

The ResNet-18 backbone is a *generic vision feature extractor*, not a third-party reconstruction product (it is not
lingbot-map). Everything downstream of the features, the depth decoder, the aleatoric confidence head, the Siamese
pose head, the se(3) exponential, the losses and the training loop, is ours.

## Depth head (aleatoric)

For a frame $I$ the depth branch outputs a raw map and a log-variance map, squashed to a positive metric depth and a
bounded aleatoric log-variance:

$$\hat D = D_{\max}\,\sigma(h_D), \qquad \log \hat\sigma^2 = \operatorname{clamp}(h_\Sigma,\,-8,\,8)$$

with $D_{\max} = 10\ \text{m}$. The per-pixel **confidence** used both to weight the loss and to filter the point
cloud at inference is $c = e^{-\log \hat\sigma^2}$ (high = reliable). At inference we keep only pixels above a
per-frame quantile of $c$ (the OUR case uses `conf_quantile = 0.6`, i.e. the top 40 % most confident pixels), which
sharpens the cloud; this is a genuine, useful feature of the learned confidence, not decoration.

The depth is supervised with a heteroscedastic (aleatoric) negative log-likelihood over valid ground-truth pixels
$\Omega$ (depth $> 0$):

$$\mathcal{L}_{D} = \frac{1}{|\Omega|}\sum_{p\in\Omega}\Big(\tfrac{1}{2}e^{-\log\hat\sigma^2_p}\,\lVert \hat D_p - D_p\rVert^2 + \tfrac{1}{2}\log\hat\sigma^2_p\Big)$$

The $\log\hat\sigma^2$ term lets the model *down-weight* pixels it cannot predict (thin structure, reflections,
depth holes) instead of being dragged by them; this is why the loss can go negative once the model is both accurate
and confident.

## Pose head (se(3))

The pose branch regresses a 6-DoF relative motion as an se(3) tangent vector $\xi = (\boldsymbol{\omega},
\mathbf{v}) \in \mathbb{R}^6$. In the `scratch` backbone a small convnet consumes the channel-stacked pair; in the
`resnet18` backbone a **Siamese** head consumes the globally-pooled ResNet features of both frames,
$\xi = \mathrm{MLP}([\,\bar f_0,\ \bar f_1\,])$, with the last layer zero-initialised so training starts at identity
motion. Our own se(3) exponential (Rodrigues form, differentiable) maps $\xi$ to a $4\times4$ transform:

$$\theta = \lVert\boldsymbol{\omega}\rVert,\quad K = [\hat{\boldsymbol{\omega}}]_\times,\quad
R = I + \sin\theta\,K + (1-\cos\theta)\,K^2,\qquad T = \begin{bmatrix} R & \mathbf{v}\\ \mathbf 0 & 1\end{bmatrix}$$

The relative-pose loss combines a rotation term (geodesic on $SO(3)$, via the trace) and a translation term against
the ground-truth relative pose $T^{\text{gt}}$ from the dataset trajectory.

## From pairs to a map

At inference the engine walks the stream, accumulating $\,{}^{w}\!T_t = {}^{w}\!T_{t-1}\,\hat T_{t-1\to t}$, and
unprojects each depth into the world via the pinhole model (`geom.unproject`, OpenCV convention, X-right/Y-down/
Z-forward), coloring points by the RGB frame and filtering by confidence. The trajectory and per-frame observer
frustums are emitted so the App can replay the map building up frame by frame.

Three things make the fused cloud geometrically consistent rather than a diffuse spray:

1. **Real intrinsics.** Each case carries the dataset's true $(f_x, f_y, c_x, c_y)$ (scaled to the working
   resolution), so the unprojection is correct. A wrong fixed field-of-view systematically bends every frame and
   misaligns the accumulation.
2. **Far-depth clamp.** Points beyond a per-scene range are dropped. A small angular pose error times a large depth
   is a large position error, so far points are where drift turns into scatter; clamping keeps the near structure
   sharp.
3. **Pose refinement ladder.** The model's per-frame depth is sharp and its relative pose is a good prior, but raw
   accumulation drifts. The engine has a three-rung refinement ladder (each falls back to the previous on failure),
   so the fused map is as consistent as the pose accuracy allows:
   - **Frame-to-frame ICP** (default, `LIDAR3D_OWN_ICP`): each predicted relative pose is refined by point-to-plane
     ICP (Open3D) on the depth clouds, initialised from the model pose and guarded (a bad frame falls back to the
     raw prior, never corrupting the trajectory). Removes most local drift.
   - **D1: global pose-graph optimization + loop closure** (opt-in, `LIDAR3D_OWN_GLOBAL=1`): Open3D multiway
     registration builds odometry edges plus loop-closure edges (spatially-near but temporally-distant frames that
     still align) and distributes the drift globally so revisited places snap together. This is the classic
     bundle-adjustment-style fix and is fully implemented.
   - **TSDF volumetric fusion** (opt-in, `LIDAR3D_OWN_TSDF=1`): integrate every confident, near depth frame into a
     truncated signed-distance volume and extract a single *denoised* surface (KinectFusion-style). Volumetric
     averaging cancels the per-frame monocular depth noise that no pose refinement can remove.

**Honest finding (why the defaults are ICP, not D1/TSDF).** D1 and TSDF are the correct tools for a *clean surface*,
but both need sub-voxel pose accuracy. At the current monocular pose accuracy (~0.37 m held-out ATE), global
optimization over-constrains single-area indoor sweeps and TSDF fuses only sparsely (frames disagree, so most of the
volume cancels out). So the shipped default is the ICP-refined raw accumulation, which is the most robust at this
accuracy. D1 and TSDF are implemented and one flag away; they become the right default the moment the pose model
improves. The real lever for a clean surface is therefore **a stronger pose model (more training data)**, not more
post-processing, which is why the training set is being grown. This is the genuine, documented limitation of
feed-forward monocular reconstruction: the per-frame depth is excellent; the fused map is bounded by pose accuracy.

## What is measured: held-out ATE

Model quality is reported as **Absolute Trajectory Error (ATE)**: run the model over a held-out sequence, accumulate
the predicted camera trajectory, align it to ground truth with a similarity transform (Umeyama), and take the RMS
position error in metres. It is a *trajectory* metric: a small per-pair pose error accumulates over the sequence, so
ATE grows with sequence length. A short case (the OUR desk case reconstructs ~60 frames after decimation) drifts far
less than the ~300-frame held-out evaluation sequence, so the *look* of the reconstruction can be tighter than the
reported ATE alone suggests. The diffuse-vs-sharp appearance is dominated by **pose drift**, which is why the pose
head (and, in the pretrained variant, its steadier pose) matters as much as depth sharpness.

## Training

`train/train_depthpose.py` trains on real TUM RGB-D (registered metric depth + ground-truth trajectory) and,
optionally with `--use_icl`, on ICL-NUIM (synthetic, *perfect* ground-truth depth). Key flags:

- `--backbone {scratch,resnet18}` — pick the encoder.
- `--use_icl` — add ICL-NUIM perfect-depth pairs (cleaner depth supervision).
- `--base`, `--size`, `--lr`, `--epochs`, `--batch` — capacity and optimisation.

Training uses **best-checkpoint early stopping**: the held-out ATE is evaluated each epoch and the checkpoint is
saved only when ATE improves (a long run can overfit and *degrade* ATE, the "diffuse" look). Every epoch's result is
appended to `experiments.jsonl` so no run is lost. See [Model history](02_model-history.md) for the full record and
[Experiments log](03_experiments-log.md) for the schema.

## Architecture reference

Working resolution 224×224. The `resnet18` variant (the deployed one):

| Block | Module | Output | Channels |
|---|---|---|---|
| Encoder (ImageNet ResNet-18, shared) | stem (conv7×7 s2 + bn + relu) | /2 | 64 |
| | maxpool + layer1 | /4 | 64 |
| | layer2 | /8 | 128 |
| | layer3 | /16 | 256 |
| | layer4 | /32 | 512 |
| Depth decoder (ours, UNet skips) | d4: up(x5)⊕x4 → conv×2 | /16 | base·4 |
| | d3: up⊕x3 | /8 | base·2 |
| | d2: up⊕x2 | /4 | base |
| | d1: up⊕x1 | /2 | base |
| | head (conv1×1) → interpolate to input | 224 | 2 (depth_raw, logvar) |
| Pose head — `siamese` (default) | global-pool x5 of both frames → MLP(1024→256→128→6) | — | 6 (se(3)) |
| Pose head — `corr` (experimental) | local correlation of x4 (9×9 window) ⊕ x4 → convnet → MLP → 6 | — | 6 (se(3)) |

- `base = 32` (decoder width). Total ~12.8 M params (ResNet-18 ~11.7 M + our decoder/pose ~1.1 M).
- Depth output: `D_max·σ(head[0])`, `D_max = 10 m`. Log-variance clamped to [−8, 8].
- The `scratch` variant replaces the encoder with a from-scratch UNet (~2.2 M params) and the pose head with a small
  6-channel-input convnet; same forward signature, zero external weights.
- se(3) exponential (`se3_exp`): our own Rodrigues form, differentiable, maps the 6-vector to a 4×4 transform.

Code: the encoder (`PretrainedEncoder`), decoder (`DepthDecoder`), pose heads (`SiamesePoseHead` / `CorrPoseHead`),
and `se3_exp` all live in `data-pipeline/lidar3dlab/model/nets/own_depthpose.py`.

## References

- Kendall & Gal, *What Uncertainties Do We Need in Bayesian Deep Learning for Computer Vision?*, arXiv:1703.04977
  (aleatoric log-variance loss).
- Umeyama, *Least-squares estimation of transformation parameters between two point patterns*, IEEE TPAMI 1991 (ATE
  alignment).
- Sturm et al., *A Benchmark for the Evaluation of RGB-D SLAM Systems*, IROS 2012 (TUM RGB-D).
- Handa et al., *A Benchmark for RGB-D Visual Odometry, 3D Reconstruction and SLAM*, ICRA 2014 (ICL-NUIM).
- He et al., *Deep Residual Learning for Image Recognition*, arXiv:1512.03385 (ResNet backbone).
