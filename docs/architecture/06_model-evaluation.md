# Architecture: model evaluation and the honesty policy

Evaluation is where a reconstruction lab is tempted to lie, and where Lidar 3D refuses to. This document
states exactly what we measure, what we deliberately do **not** claim, and why the `train` stage being a no-op
is honest rather than a gap.

Source: `stages/evaluate.py`, surfaced on the web's Experiments / Benchmark pages and stored in each
manifest's `metrics` block.

## What we measure

`evaluate.run(result)` computes trajectory- and cloud-quality metrics that are fully determined by the
reconstruction output, so they are always real:

| Metric | Meaning |
|---|---|
| `n_points` | size of the fused (post-refine) cloud |
| `n_frames` | frames actually processed |
| `path_length_m` | metric length of the recovered camera/sensor trajectory |
| `bbox_extent_m` | world-space extent of the reconstruction (x, y, z) |
| `mean_conf` | mean per-frame depth confidence (camera engine); 1.0 for synthetic/LiDAR |
| `n_quality_frames` | count of frames scored by feature_extraction (luma/sharpness) |

These are metric (in metres) because the camera engine's scale is fixed by the anchor context
(`s = mean L2 norm of the anchor cloud`), so `path_length_m` and `bbox_extent_m` are meaningful physical
quantities, not arbitrary units.

## What we do NOT claim: no faked ATE/RPE

Absolute Trajectory Error (ATE) and Relative Pose Error (RPE) are the standard SLAM accuracy metrics, and they
require **ground-truth poses**. The bundled example sequences (`oxford`, `university`, `loop`, `courthouse`)
ship with the lingbot-map repo and carry **no** ground-truth poses. So `evaluate.run` sets:

```python
"ate_m": None, "rpe_trans": None, "rpe_rot": None,
"gt": "none (example sequences carry no ground-truth poses; ATE/RPE reported only when GT is provided)",
```

We report `None` and say why, rather than inventing a number by comparing the reconstruction to itself, or by
aligning against a proxy and calling it truth. An ATE of "0.00" that was never computed against real GT would
be worse than useless: it would be a lie the whole product's credibility rests against. When a case *does*
carry GT poses, the stage is the place to compute ATE/RPE (Umeyama alignment, then the standard errors) and
report them honestly; until then, "no GT" is the correct answer.

This is the same discipline as the gate ([03](03_the-gate.md)): a claim in this product is a measurement or it
is absent. The web Benchmark page shows the paper's own reported SOTA numbers (for example Oxford-Spires ATE
6.42, ETH3D F1 98.98) **cited as the paper's**, clearly separated from what this lab measures on its own
hardware. We never present someone else's benchmark as ours.

## Why `train` is a no-op, and why that is honest

The `train` stage returns a fixed info dict and fits nothing (see [05](05_staged-pipeline.md)). This is not a
missing feature; it is a correct statement about the product. The reconstruction engine is the **pretrained**
lingbot-map foundation model (~37k GPU-hours of training, Apache-2.0), used as-is. There is no per-product
model to fit, so "training" would be theatre. The manifest records `pretrained: True, trained_here: False`, so
the artifact is explicit that no local training happened.

The archetype keeps the stage name (frozen base) and documents the no-op, rather than deleting it, for two
reasons: uniformity across the CAOS labs, and a real future home. A genuine local training job does have a
place here: an ONNX distillation of a low-VRAM sub-model (for example a single-image depth preview that could
eventually run in the browser) would be fit in `train` and evaluated in `evaluate`. Until that exists, the
honest thing is to say the stage is dormant, which it does.

## The distinction that matters: "accurate" means what, exactly

For any surrogate or emulator, "accurate" has to be qualified. This product does not currently ship a
surrogate (the engine is the foundation model itself), so the question is simpler here than in the physics
labs, but the discipline is the same: if a future distilled preview model is added, its evaluation must state
that "accurate" means *agrees with the full lingbot-map output* on held-out sequences, **not** *matches
survey-grade ground truth*, unless GT is actually available. Calibration/reference data must stay strictly
disjoint from validation data; a metric computed on the data used to tune the model is not a validation
metric.

## Honesty policy, summarized

- Numbers come from the engine and the committed artifacts, never from a claim.
- Metrics that need ground truth are reported only when ground truth exists; otherwise `None` + a stated
  reason. No faked ATE/RPE.
- The synthetic engine is clearly labelled synthetic (`real_or_synthetic: "synthetic"`, engine label
  `"synthetic-corridor (CPU)"`); it is a real procedural reconstruction, not a stand-in pretending to be a
  camera bake.
- The paper's SOTA numbers are cited as the paper's, on the Benchmark page, separate from this lab's own
  measurements.
- The LiDAR lane's non-determinism is disclosed ([02](02_determinism-and-trace.md)); we do not claim what we
  cannot guarantee.
- The engine's own stated limitations (no loop closure, trajectory-memory compression loss, no test-time
  optimization) are documented in the research notes and drive the lab's novel agenda, rather than being
  papered over.

## See also

- [03: the gate](03_the-gate.md): "measured, not claimed" applied to the lane verdict.
- [05: the staged pipeline](05_staged-pipeline.md): where evaluate sits and what train does.
- [08: the two data contracts](08_data-contracts.md): how the metrics travel in the manifest.
