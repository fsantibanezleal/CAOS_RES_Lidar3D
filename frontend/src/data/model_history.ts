// The complete, honest record of every model/experiment in this lab, shipped in the product so the history is
// visible on-site (not only in the repo). Kept in sync with docs/models/02_model-history.md and the append-only
// models/own-depthpose/experiments.jsonl. Rows before the JSONL log existed are backfilled. Held-out ATE is RMS
// trajectory error (m) on TUM freiburg3_long_office_household (~300 pairs), Umeyama-aligned; lower is better.
export type ModelRun = {
  id: string;
  run: string;
  backbone: 'scratch' | 'resnet18' | 'dinov2-vitb' | 'window_pgo' | 'probes' | 'sensor+pgo';
  data: string;
  ate: string;       // metres, or a note
  deployed: 'live' | 'yes-superseded' | 'no' | 'pending';
  notes_en: string;
  notes_es: string;
};

export const MODEL_HISTORY: ModelRun[] = [
  {
    id: 'M1', run: 'first own model (v0.06.000)', backbone: 'scratch', data: 'TUM RGB-D, 5 seq (~9.9k frames)',
    ate: '~0.20', deployed: 'yes-superseded',
    notes_en: 'first honest from-scratch depth+pose (2.2 M params); baked our desk case.',
    notes_es: 'primer depth+pose honesto desde cero (2.2 M params); precalculó el caso propio (escritorio).',
  },
  {
    id: 'M2', run: 'long run, no early-stop', backbone: 'scratch', data: 'TUM RGB-D',
    ate: '0.49', deployed: 'no',
    notes_en: 'overfit: a long run degraded ATE (the "diffuse" look); motivated best-checkpoint early stopping.',
    notes_es: 'sobreajuste: una corrida larga degradó el ATE (el aspecto "difuso"); motivó el early-stopping por mejor checkpoint.',
  },
  {
    id: 'M3', run: 'photometric run', backbone: 'scratch', data: 'TUM RGB-D',
    ate: 'crashed', deployed: 'no',
    notes_en: 'self-supervised photometric loss with predicted pose; crashed without saving.',
    notes_es: 'pérdida fotométrica auto-supervisada con pose predicha; se cayó sin guardar.',
  },
  {
    id: 'M4', run: 'early-stopping retrain (v0.09.004)', backbone: 'scratch', data: 'TUM RGB-D',
    ate: '0.29', deployed: 'live',
    notes_en: 'added best-checkpoint early stopping; re-baked our case (coherent per-frame depth). This baked artifact is what the site currently serves.',
    notes_es: 'agregó early-stopping por mejor checkpoint; re-precalculó el caso propio (profundidad por cuadro coherente). Este artefacto precalculado es el que el sitio sirve hoy.',
  },
  {
    id: 'M5', run: 'extra-losses experiment (v0.10.x)', backbone: 'scratch', data: 'TUM RGB-D',
    ate: '0.29 → 0.56', deployed: 'no',
    notes_en: 'Negative result: photometric + smoothness + cosine + higher LR destabilised pose and hurt ATE; reverted to simple supervised.',
    notes_es: 'Resultado negativo: fotométrica + suavidad + coseno + LR alto desestabilizaron la pose y empeoraron el ATE; se revirtió a supervisado simple.',
  },
  {
    id: 'M6', run: 'simple retrain + conf 0.6', backbone: 'scratch', data: 'TUM RGB-D',
    ate: '0.4344', deployed: 'no',
    notes_en: 'run-to-run instability landed worse than M4; re-baked our case with conf 0.6 (54,665 pts) but 0.43 m pose was still diffuse, so reverted to keep M4 live. Its baked artifact is preserved in git.',
    notes_es: 'la inestabilidad entre corridas quedó peor que M4; re-precalculó el caso propio con conf 0.6 (54.665 pts) pero la pose de 0.43 m seguía difusa, así que se revirtió para mantener M4 en vivo. Su artefacto precalculado está preservado en git.',
  },
  {
    id: 'M7', run: 'pretrained backbone + ICP (v0.11.000)', backbone: 'resnet18',
    data: 'TUM RGB-D (5 seq) + ICL-NUIM, 7329 pairs',
    ate: '0.37', deployed: 'yes-superseded',
    notes_en: 'ImageNet ResNet-18 shared by depth decoder + Siamese pose head (12.8 M), best held-out ATE 0.37 m. Inference adds real per-dataset intrinsics + far-depth clamp + frame-to-frame ICP pose refinement (Open3D). First own-model deployment across 8 scenes at 240 frames; superseded by M8.',
    notes_es: 'ResNet-18 de ImageNet compartido por decoder de profundidad + cabeza de pose Siamese (12.8 M), mejor ATE held-out 0.37 m. La inferencia agrega intrínsecas reales + recorte de profundidad lejana + refinamiento de pose por ICP (Open3D). Primer despliegue del modelo propio en 8 escenas a 240 frames; reemplazado por M8.',
  },
  {
    id: 'M8', run: 'best recovery run (v0.12.001, LIVE)', backbone: 'resnet18',
    data: 'TUM RGB-D (winning 4-seq subset) + ICL-NUIM, 11k pairs',
    ate: '0.28', deployed: 'live',
    notes_en: 'The deployed own model: ResNet-18 + Siamese, best held-out ATE 0.28 m (beats M7 0.37 m). Deployed across all 8 OWN scenes with the ICP refinement ladder. Negative results (correlation pose head, more-data-11-seq) kept in the record.',
    notes_es: 'El modelo propio desplegado: ResNet-18 + Siamese, mejor ATE held-out 0.28 m (supera el 0.37 m de M7). Desplegado en las 8 escenas OWN con el ladder de refinamiento ICP. Los resultados negativos (cabeza de correlación, más-datos-11-seq) quedan en el registro.',
  },
  {
    id: 'M9', run: 'frozen DINOv2 ViT-B (DepthAnything recipe)', backbone: 'resnet18',
    data: 'TUM RGB-D (4-seq) + ICL-NUIM, 11k pairs',
    ate: '0.61', deployed: 'no',
    notes_en: 'Frozen DINOv2 ViT-B + a DPT-style decoder (the same foundation-backbone family the reference SOTA uses): 89.6 M total but only 3.0 M trainable at 0.65 GB VRAM, proving 8 GB is not the constraint. Measured with a new depth metric: depth-AbsRel 0.22 vs the ResNet 0.38 = 42% better depth. But the pose ATE (0.61 m) is worse: the trajectory is capped by the regression pose head, not the backbone. Post-hoc global bundle adjustment on that pose (M-A) did not clean the map. On modest hardware depth is cheap and pose is the bottleneck; the next lever is a geometric (differentiable-BA) pose, not more capacity.',
    notes_es: 'DINOv2 ViT-B congelado + decoder estilo DPT (la misma familia de backbone fundacional que usa el SOTA de referencia): 89.6 M totales pero solo 3.0 M entrenables a 0.65 GB de VRAM, probando que los 8 GB no son el límite. Medido con una métrica de profundidad nueva: depth-AbsRel 0.22 vs 0.38 del ResNet = 42% mejor profundidad. Pero el ATE de pose (0.61 m) es peor: la trayectoria la limita la cabeza de pose de regresión, no el backbone. El bundle adjustment global post-hoc sobre esa pose (M-A) no limpió el mapa. En hardware modesto la profundidad es barata y la pose es el cuello de botella; la siguiente palanca es una pose geométrica (BA diferenciable), no más capacidad.',
  },
  {
    id: 'M-C', run: 'Estela-W: windowed pose-graph (differentiable BA)', backbone: 'window_pgo',
    data: 'TartanGround + TUM windows (4483)',
    ate: '3.16 (geo edges)', deployed: 'no',
    notes_en: 'The differentiable windowed pose-graph (window_pgo): per-edge relative-pose measurements (consecutive + skip) jointly optimized per window. Trained by supervising the measurements directly (back-propagating through the solver goes NaN from a cold start); solver runs forward-only at inference. The fusion works (per-window drift -45% vs chaining the same measurements) but fusing the weak geometric front-end does not beat M8: the front-end is the ceiling, not the fusion. The solver itself found production use in Track B (see the RGBD row).',
    notes_es: 'El pose-graph por ventanas diferenciable (window_pgo): mediciones de pose relativa por arista (consecutivas + salto) optimizadas conjuntamente por ventana. Entrenado supervisando las mediciones directamente (retropropagar por el solver da NaN desde cero); el solver se ejecuta solo-forward en inferencia. La fusión funciona (drift por ventana -45% vs encadenar las mismas mediciones) pero fusionar el front-end geométrico débil no supera a M8: el techo es el front-end, no la fusión. El solver encontró uso productivo en Track B (ver la fila RGBD).',
  },
  {
    id: 'EXP', run: 'refinement + paradigm probes (honest negatives)', backbone: 'probes',
    data: 'TUM long_office/desk/pioneer',
    ate: 'raw 0.124 beats all', deployed: 'no',
    notes_en: 'Three decisive probes. (1) Geometric post-processing worsens the deployed trajectory: raw model chain 0.124 m beats ICP 0.39, windowed BA 0.63, global PGO 0.73 on matched frames. (2) The vendored pointmap engine ties Estela in shape under the fair Sim(3) protocol (0.111 vs 0.124 m) but is up-to-scale (~0.11x), confirming metric scale as the blocker, not the paradigm. (3) A metric-depth geometric pose (SIFT+PnP on Depth Anything V2) reaches 0.031-0.034 m with an oracle per-scene scale, ~10x better than deployed, but no monocular signal recovers that scale (jerk and reprojection are degenerate, path-length anchoring is biased): the classical monocular scale ambiguity, measured.',
    notes_es: 'Tres sondas decisivas. (1) El post-procesamiento geométrico empeora la trayectoria desplegada: la cadena cruda del modelo 0.124 m supera a ICP 0.39, BA por ventanas 0.63, PGO global 0.73 en frames iguales. (2) El motor pointmap vendorizado empata con Estela en forma bajo el protocolo justo Sim(3) (0.111 vs 0.124 m) pero sale sin escala (~0.11x), confirmando la escala métrica como el bloqueador, no el paradigma. (3) Una pose geométrica con depth métrico (SIFT+PnP sobre Depth Anything V2) llega a 0.031-0.034 m con escala oráculo por escena, ~10x mejor que lo desplegado, pero ninguna señal monocular recupera esa escala (jerk y reproyección son degeneradas, el anclaje por longitud de camino está sesgado): la ambigüedad de escala monocular clásica, medida.',
  },
  {
    id: 'RGBD', run: 'Track B: RGB + sensor depth (LIVE)', backbone: 'sensor+pgo',
    data: 'TUM RGB-D (Kinect depth stream)',
    ate: '0.024-0.085', deployed: 'yes-superseded',
    notes_en: 'The two-track family goes live: SIFT + PnP on the real Kinect depth (metric by construction, the scale blocker disappears at the source) + the M-C windowed pose-graph fusing the strong metric edges (a further 7-26% drift cut; its first production use). Office 0.085 m, desk 0.034, pioneer 0.024 vs 0.28 m RGB-only. Cases RGBD_tum_office/desk mirror the RGB-only OWN_* scenes for an honest side-by-side. Sensor holes stay holes; nothing is hallucinated.',
    notes_es: 'La familia de dos tracks entra en producción: SIFT + PnP sobre la profundidad Kinect real (métrica por construcción, el bloqueador de escala desaparece en el origen) + el pose-graph por ventanas M-C fusionando las aristas métricas fuertes (un recorte adicional de drift de 7-26%; su primer uso productivo). Office 0.085 m, desk 0.034, pioneer 0.024 vs 0.28 m RGB-only. Los casos RGBD_tum_office/desk reflejan las escenas RGB-only OWN_* para una comparación honesta lado a lado. Los huecos del sensor quedan como huecos; nada se alucina.',
  },
  {
    id: 'I1', run: 'Track B tuning: depth-edge guard (LIVE) + learned-matcher negative', backbone: 'sensor+pgo',
    data: 'TUM RGB-D (Kinect depth stream)',
    ate: '0.014-0.040', deployed: 'live',
    notes_en: 'A performance pass over Track B. Win (shipped): a depth-edge guard that keeps only matches whose local sensor-depth patch is filled and flat, since a 1 px match error at a depth discontinuity back-projects to a large 3D error. Matcher-independent, no starvation (it falls back to the plain valid set on depth-rich scenes): SIFT ATE office 0.077 to 0.038 m (+51%), desk 0.041 to 0.032 (+22%), desk2 0.016 to 0.014, with pioneer/xyz unchanged. Negative (measured, not shipped as default): a DISK + LightGlue learned matcher wins +13-27% over a plain chain with 2-3x more inliers, but end-to-end (with fusion + the guard) SIFT beats it on 3/5 scenes, because the guard removes exactly the noisier matches the learned matcher added. Kept available opt-in for hard/blurred imagery where the extra inliers add robustness. Lesson: the isolated probe overclaimed; the deployed measurement is the truth.',
    notes_es: 'Una pasada de rendimiento sobre Track B. Ganancia (desplegada): un guard de bordes de profundidad que conserva solo las coincidencias cuyo parche local de profundidad del sensor está lleno y es plano, porque un error de 1 px en una discontinuidad de profundidad se retroproyecta a un gran error 3D. Independiente del emparejador, sin inanición (cae al conjunto válido simple en escenas ricas en profundidad): ATE de SIFT office 0.077 a 0.038 m (+51%), desk 0.041 a 0.032 (+22%), desk2 0.016 a 0.014, con pioneer/xyz sin cambio. Negativo (medido, no desplegado por defecto): un emparejador aprendido DISK + LightGlue gana +13-27% sobre una cadena simple con 2-3x más inliers, pero de extremo a extremo (con fusión + el guard) SIFT lo supera en 3/5 escenas, porque el guard elimina justo las coincidencias más ruidosas que el emparejador añadía. Se mantiene disponible opt-in para imágenes difíciles/borrosas donde los inliers extra dan robustez. Lección: la sonda aislada sobreestimó; la medición desplegada es la verdad.',
  },
  {
    id: 'I3', run: 'Track B cloud quality: TSDF surface fusion (LIVE, default)', backbone: 'sensor+pgo',
    data: 'TUM RGB-D (Kinect depth stream)',
    ate: 'same poses', deployed: 'live',
    notes_en: 'Cloud-quality pass, orthogonal to ATE (the poses are unchanged). The raw per-frame accumulation is replaced by TSDF volumetric fusion of the sensor depth (KinectFusion-style, 12 mm voxels): every valid, near depth frame is integrated into a truncated signed-distance volume at its solved pose, then a single denoised surface is extracted. Track B poses are now tight enough (0.014-0.040 m after I1) that the volumetric averaging cancels the per-frame sensor noise and the double-surfaces raw accumulation showed, giving a markedly cleaner surface at ~half the points (office 150k to 78k, desk to 58k). Screenshot-verified clean across all 5 scenes, small desk to the large pioneer robot run. Falls back to raw accumulation when open3d is absent, so the live lane matches replay. TSDF now becomes the default on Track B because its poses finally support it, mirroring why it stays opt-in on the RGB-only 0.37 m poses (there it carves sparsely).',
    notes_es: 'Pasada de calidad de nube, ortogonal al ATE (las poses no cambian). La acumulación cruda por frame se reemplaza por fusión volumétrica TSDF de la profundidad del sensor (estilo KinectFusion, vóxeles de 12 mm): cada frame de profundidad válido y cercano se integra en un volumen de distancia con signo truncada en su pose resuelta, y luego se extrae una única superficie sin ruido. Las poses de Track B ya son suficientemente ajustadas (0.014-0.040 m tras I1) para que el promediado volumétrico cancele el ruido del sensor por frame y las dobles superficies que mostraba la acumulación cruda, dando una superficie mucho más limpia con ~la mitad de puntos (office 150k a 78k, desk a 58k). Verificado por captura en las 5 escenas, del desk pequeño a la corrida robot pioneer grande. Cae a acumulación cruda si open3d no está, así el lane en vivo coincide con la reproducción. TSDF pasa a ser el default en Track B porque sus poses por fin lo permiten, reflejando por qué queda opt-in en las poses RGB-only de 0.37 m (allí talla de forma dispersa).',
  },
];
