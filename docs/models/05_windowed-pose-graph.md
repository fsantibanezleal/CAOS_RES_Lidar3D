# Estela-W: the windowed pose-graph model (M-C)

The multi-frame variant of **Estela**, our depth+pose reconstruction net. Where the per-pair
[Estela](01_own-depth-pose.md) predicts one relative pose per consecutive pair and the engine chains those pairs
into a trajectory, Estela-W predicts a relative-pose **measurement per edge of a sliding window** (consecutive
*and* skip edges) and solves for all the window's poses **jointly** with a differentiable pose-graph optimisation.
The joint solve is what lets it beat the drift that pure per-pair chaining accumulates.

(Estela is Spanish for the wake a moving body leaves and also a stele, a standing carved stone: the net turns a
moving camera into a trajectory and a 3D structure. M-C / "Estela-W" is its windowed-bundle-adjustment form.)

Code: `data-pipeline/lidar3dlab/model/nets/window_ba.py` (the model + the solver),
`data-pipeline/lidar3dlab/train/train_window.py` (training + evaluation).

## Why a window (the motivation)

Every per-pair pose estimator drifts. Small consecutive errors accumulate coherently along the trajectory: measured
on our own models, the deployed per-pair M8 reaches 0.28 m ATE on TUM `long_office`, but the single-pair geometric
head (M-B) alone chains to 1.21 m. The state of the art (DROID-SLAM, DPVO, DINO-VO) fixes this with a multi-frame
**bundle-adjustment / pose-graph** step that optimises a window of poses for global consistency instead of one pair
at a time. M-C is our differentiable version of that step.

A window of $N$ frames has more constraints than a chain: besides the $N-1$ consecutive edges it has **skip edges**
(frame $i$ to frame $i+2$, and further). Those extra edges over-constrain the poses, so a joint solve can average
out per-edge noise that a pure consecutive chain would instead integrate.

## Architecture

`WindowDepthPose` reuses the depth machinery of the own model (a pretrained/frozen backbone, the aleatoric depth
decoder, the metric-depth-seeded geometric correspondence head `GeoPoseHead`), but instead of one pose per pair it
emits one measurement per window edge and fuses them:

1. Encode the $N$ frames, decode per-frame depth $\hat D$ and confidence.
2. For each edge $(i,j)$ in the window, the geometric head produces a **relative-pose measurement**
   $Z_{ij}\approx T_i^{-1}T_j$ and a scalar confidence $w_{ij}$ from the two frames' features and metric depths
   (`GeoPoseHead.measure`).
3. `window_pgo` solves for the absolute poses $T_0\dots T_{N-1}$ (with $T_0$ anchored to identity) that best satisfy
   all edges at once.

The forward is split into two methods so training and inference can use different paths (see the pivot below):

| Method | Returns | Used by |
|---|---|---|
| `measure_edges(rgbs, K, edges)` | depth, logvar, per-edge $Z_{ij}$, $w_{ij}$ (no solve) | training (supervised directly) + inference |
| `forward(rgbs, K, edges)` | `measure_edges` then `window_pgo` fused poses | inference |

`window_edges(n, skip)` builds the edge set: all consecutive pairs $(i,i{+}1)$ plus skip connections $(i,i{+}j)$ for
$j\le\texttt{skip}$. For $N=6,\ \texttt{skip}=2$ that is 5 consecutive + 4 skip = 9 edges.

## The differentiable pose-graph solve

Poses are parameterised by their se(3) tangents $\xi_1\dots\xi_{N-1}$ (with $\xi_0\equiv 0$ the anchor), so
$T_i=\exp(\xi_i^\wedge)$. For an edge $(i,j)$ with measurement $Z_{ij}$ the residual is the deviation of the
predicted-vs-measured relative pose from identity, taken as the $3\times4$ block (no SE(3) log, fully
differentiable, an excellent proxy for the geodesic residual at the small errors a BA operates in):

$$E_{ij} = Z_{ij}^{-1}\,\big(T_i^{-1}T_j\big), \qquad r_{ij} = \operatorname{vec}\!\big(E_{ij}^{[:3,:]}-[\,I\mid 0\,]\big)\in\mathbb R^{12}.$$

Stacking all edges gives $r(\xi)$. Each iteration is a Levenberg-Marquardt-damped Gauss-Newton step with the
autograd Jacobian $J=\partial r/\partial\xi$, per-edge confidence weights $W=\operatorname{diag}(w)$, and a norm-clamped update:

$$\big(J^\top W J + \lambda I\big)\,\Delta\xi = -\,J^\top W\,r, \qquad \xi \leftarrow \xi + \operatorname{clip}(\Delta\xi).$$

The whole solve is differentiable (`create_graph=True` on the Jacobian) so, in principle, the head can be trained
*through* it. Strong LM damping, the step clamp, and NaN/Inf scrubbing keep $J^\top W J + \lambda I$ well
conditioned even when the measurements are degenerate.

## The training-path pivot (the decisive design choice)

Training *through* `window_pgo` is a second-order problem (a backward through a solve that already contains a
Jacobian). With an **untrained** head the measurements are degenerate, the inner Gauss-Newton is ill-posed, and the
second-order backward goes **NaN**. Damping stabilises the forward solve but not that backward from a cold start.

So we do **not** train through the solver. We supervise the per-edge measurements **directly**: for every window
edge $(i,j)$ the head must predict the ground-truth relative pose $T_i^{-1}T_j$ (available exactly from the
dataset's poses, for consecutive *and* skip edges). That is a first-order, stable loss. `window_pgo` is then used
**forward-only at inference** to fuse the learned edges. The synthetic self-test in `window_ba.py` already shows
that, given good-ish per-edge measurements, the joint solve beats a pure consecutive chain; the trainer's job is to
make the measurements good on real data.

The per-edge loss is aleatoric, so the head learns a **calibrated confidence** that `window_pgo` can weight by:

$$\mathcal L_{\text{meas}} = \frac1{|\mathcal E|}\sum_{(i,j)\in\mathcal E} \Big( w_{ij}\,\big\lVert Z_{ij}\ominus T_i^{-1}T_j\big\rVert - \beta\log w_{ij}\Big),$$

where $\lVert\cdot\ominus\cdot\rVert$ is rotation (Frobenius) plus translation ($L_1$) error and $\beta$ is a small
confidence regulariser. The depth branch keeps its aleatoric metric-depth NLL from the own model.

## Data

`TartanGroundWindows` and `TUMWindows` (`train/dataset_tum.py`) yield $N$-frame windows: the RGB stack, per-frame
depth, and the absolute poses anchored so frame 0 is identity (in our optical frame). They reuse the pair loaders'
frame index. TartanGround supplies perfect synthetic poses (and long skip edges); TUM supplies real indoor
trajectories so M-C can be evaluated on the same `long_office` sequence the per-pair M8 is scored on.

## Evaluation

Held out on a full sequence, composing overlapping windows (window stride $=N-1$, so each window shares its first
frame with the previous window's last). Two metrics, and for each an ablation on the *same* measurements:

- **ATE (fused vs chain).** The umeyama-aligned RMS trajectory error of the `window_pgo` fused trajectory, and, as
  the ablation, of a trajectory built by chaining only the consecutive measurements (what a per-pair estimator
  does). This is comparable to the own model's ATE.
- **Per-window drift (fused vs chain).** The mean translation error of a single window's $N$ poses vs ground truth,
  anchored at the window's own frame 0. It is scale-normalised to one short window, so it isolates the fusion gain
  from long-trajectory accumulation, which the full-trajectory ATE cannot.

Reporting fused *and* chain makes the value of the joint solve explicit rather than assumed.

## Results

- **Mechanism (synthetic).** On the noisy-window self-test the joint solve cuts drift from 0.0775 m to 0.0304 m
  (61% less) vs chaining single pairs, and gradients flow to the measurements (`tests/test_window_ba.py`).
- **Training is stable.** Warm-started from the M8 depth net, the per-edge error drops from about 3 m (untrained
  head) toward the low tens of centimetres with no NaN, confirming the pivot.
- **Fusion beats chaining on real data.** Even before the head is trained, on TUM `long_office` the per-window drift
  reads fused 0.30 m vs chain 1.29 m (about 4x better), and the fused ATE beats the chained ATE.

The definitive comparison against the deployed per-pair M8 (0.28 m on TUM `long_office`), from a run trained on
TartanGround + TUM windows and evaluated on `long_office`, is recorded in
[the model history](02_model-history.md) and the [experiments log](03_experiments-log.md) as it completes.

## How to run

```bash
# smoke (1 step + 1 eval; add CUDA_VISIBLE_DEVICES=-1 to force CPU)
PYTHONPATH=data-pipeline python -m lidar3dlab.train.train_window --smoke --eval_tum \
    --init "$LIDAR3D_MODELS_ROOT/own-depthpose/own-depthpose.pt"

# train on TartanGround + TUM windows, evaluate on TUM long_office (like-for-like vs M8)
PYTHONPATH=data-pipeline python -m lidar3dlab.train.train_window --epochs 4 --batch 4 \
    --window 6 --skip 2 --use_tum --eval_tum \
    --init "$LIDAR3D_MODELS_ROOT/own-depthpose/own-depthpose.pt"
```

Checkpoints go to `LIDAR3D_MODELS_ROOT/own-depthpose/window-mc.pt` (canonical) plus a per-run archive; the per-pair
`own-depthpose.pt` is never clobbered. Every epoch appends a row to `experiments.jsonl`.
