# 05 · The in-app Architecture / "How it works" modal (ADR-0058)

Every CAOS/Faena web app **MUST** ship an in-app **Architecture / "How it works"** modal, opened by an
always-visible **ⓘ button in the header**. It is the fast visual proof the app is a *real, complete system*,
not a demo. The chrome (button + modal) comes from the shared shell; each product supplies its diagrams +
copy. This guide specifies **what CAOS_RES_Lidar3D's modal must show** so it is at full depth, not a generic
placeholder.

Binding decision: `ADR-0058-in-app-architecture-modal.md` (in CAOS_MANAGE). Reference implementations: Veta,
Circuita.

---

## 1. What you inherit from the template

- **Chrome**: `@fasl-work/caos-app-shell` (>= **0.1.2**) exposes the ⓘ button + the `ArchitectureModal`. The
  `ShellConfig` gained an `architecture` field; present ⇒ the button appears.
- **Five themed placeholder SVGs** in `frontend/public/svg/tech/`: `01-the-app.svg`, `02-lanes.svg`,
  `03-web-flow.svg`, `04-the-science.svg`, `05-data-contracts.svg`. Every color is a shell CSS-variable token
  (`--color-surface`, `--color-border`, `--color-accent`, `--color-fg`, `--color-good`, `--color-warn`, …) so
  the diagram repaints with the active light/dark theme.
- **A paste-ready config**: `frontend/src/architecture.ts.txt` with the five ADR-0058 tabs wired to the SVGs
  and bilingual ES/EN bodies.

## 2. Wire it (per product)

1. **Copy** `frontend/src/architecture.ts.txt` to `frontend/src/architecture.ts`.
2. **Specialise** the two product tabs (`app`, `science`) for Lidar3D (§3–4); the generic tabs (`lanes`,
   `web-flow`, `design`) are reusable as-is (§5).
3. **Pass it to the shell** in `frontend/src/main.tsx` (`architecture` field of `shellConfig`), and **pin** the
   shell to `^0.1.2` in `frontend/package.json`.

## 3. The `app` tab (product): must show

The domain in one picture: **problem, input, method, value**, specifically for streaming reconstruction:

- **Problem:** a moving camera (or a LiDAR), recover the **camera trajectory + a dense metric 3D map**,
  online, feed-forward, with **no per-scene optimization**.
- **Input:** an ordered RGB video/frame folder (intrinsics-free, self-calibrating) **or** LiDAR scans.
- **Method (named honestly):** the **lingbot-map** streaming engine (arXiv:2604.14141) for camera; **Open3D
  point-to-plane ICP** (KISS-ICP-swappable) for LiDAR.
- **Value / output:** camera-to-world 6-DOF pose per frame, dense metric depth + confidence, and a fused
  RGB-colored world point cloud, rendered live in the App as a three.js cloud + camera-frustum trajectory +
  per-frame depth + stats.

Replace `public/svg/tech/01-the-app.svg` with that flow and edit the `app` tab `body_en`/`body_es`.

## 4. The `science` tab (product): must show the real algorithm + equations

This is the non-negotiable depth tab. It must present the genuine engine, not hand-waving. Include:

- The **Geometric Context Transformer**: frozen DINOv2 ViT (patch-14) + 24 alternating frame/cross-frame
  attention blocks, and the **three contexts**, anchor (first $n$ frames, sets metric scale
  $s = \frac{1}{|X|}\sum \lVert x\rVert_2$), pose-reference window ($k$ recent frames, full tokens), trajectory
  memory (6 tokens/frame, Video-RoPE) ([theory 02](../theory/02_geometric-context-transformer.md)).
- The **paged KV cache** (why it is ~20 FPS over 10k+ frames; the ~80× token reduction
  $(n{+}k)M + 6T$ vs $MT$).
- The **depth-to-world unprojection** equation
  $X_{\text{world}} = R_{c2w}\big[\tfrac{u-c_x}{f_x}D,\ \tfrac{v-c_y}{f_y}D,\ D\big]^\top + t_{c2w}$
  and the `absT_quaR_FoV` pose encoding + self-calibration ([theory 03](../theory/03_pointmaps-and-geometry.md)).
- For LiDAR: the **point-to-plane ICP** residual $E(T)=\sum_j((Tp_j - q_j)\cdot n_j)^2$ and the scan-to-scan
  odometry chain ([theory 04](../theory/04_lidar-odometry.md)).

KaTeX is already in the frontend, so render the equations. Replace `public/svg/tech/04-the-science.svg` with a
diagram of the GCT + the unprojection and edit the `science` tab body.

## 5. The generic tabs (keep; tweak only if you deviate)

| id | tab | must show (Lidar3D specifics) |
|----|-----|------------------------------|
| `lanes` | Lanes: web / offline / compute | **offline** = the real lingbot-map engine bakes artifacts on a GPU; **replay** = the static SPA renders them; **live** = the dormant local-GPU API. Note there is **no browser-live engine** (the model is too heavy). |
| `web-flow` | Web-app flow | the App **replays** committed artifacts (not live recompute here); the 6 pages; the contract mirror (`io/schema.py` ↔ `contract.types.ts`); `copy-data.mjs`; GitHub Pages deploy. |
| `design` | Data contracts / design | **CONTRACT 1** (RGB/LiDAR ingestion gate: accept/reject/flag, [guide 02](02_bring-your-own-data.md)) + **CONTRACT 2** (the artifact manifest) + the measured lane gate + cases-by-category. |

Add domain tabs if useful (never *fewer* than the five).

## 6. Verify before deploy

The mandatory screenshot-verify step **must open the modal and confirm every tab renders its diagram (themed,
no broken SVG) + its text with no error**, in both light and dark. A product is **not "done"** without the ⓘ
Architecture modal at full depth: it is a non-negotiable row in the product-quality bar.
