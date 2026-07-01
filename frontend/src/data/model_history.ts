// The complete, honest record of every model/experiment in this lab, shipped in the product so the history is
// visible on-site (not only in the repo). Kept in sync with docs/models/02_model-history.md and the append-only
// models/own-depthpose/experiments.jsonl. Rows before the JSONL log existed are backfilled. Held-out ATE is RMS
// trajectory error (m) on TUM freiburg3_long_office_household (~300 pairs), Umeyama-aligned; lower is better.
export type ModelRun = {
  id: string;
  run: string;
  backbone: 'scratch' | 'resnet18';
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
    notes_en: 'first honest from-scratch depth+pose (2.2 M params); baked the OUR desk case.',
    notes_es: 'primer depth+pose honesto desde cero (2.2 M params); horneó el caso OUR (escritorio).',
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
    notes_en: 'added best-checkpoint early stopping; re-baked the OUR case (coherent per-frame depth). This baked artifact is what the site currently serves.',
    notes_es: 'agregó early-stopping por mejor checkpoint; re-horneó el caso OUR (depth por cuadro coherente). Este artefacto horneado es el que el sitio sirve hoy.',
  },
  {
    id: 'M5', run: 'extra-losses experiment (v0.10.x)', backbone: 'scratch', data: 'TUM RGB-D',
    ate: '0.29 → 0.56', deployed: 'no',
    notes_en: 'HONEST negative result: photometric + smoothness + cosine + higher LR destabilised pose and hurt ATE; reverted to simple supervised.',
    notes_es: 'resultado negativo HONESTO: fotométrica + suavidad + coseno + LR alto desestabilizaron la pose y empeoraron el ATE; se revirtió a supervisado simple.',
  },
  {
    id: 'M6', run: 'simple retrain + conf 0.6', backbone: 'scratch', data: 'TUM RGB-D',
    ate: '0.4344', deployed: 'no',
    notes_en: 'run-to-run instability landed worse than M4; re-baked OUR with conf 0.6 (54,665 pts) but 0.43 m pose was still diffuse, so reverted to keep M4 live. Its baked artifact is preserved in git.',
    notes_es: 'la inestabilidad entre corridas quedó peor que M4; re-horneó OUR con conf 0.6 (54.665 pts) pero la pose de 0.43 m seguía difusa, así que se revirtió para mantener M4 en vivo. Su artefacto horneado está preservado en git.',
  },
  {
    id: 'M7', run: 'pretrained backbone + ICP (v0.11.000)', backbone: 'resnet18',
    data: 'TUM RGB-D (5 seq) + ICL-NUIM, 7329 pairs',
    ate: '0.37', deployed: 'yes-superseded',
    notes_en: 'ImageNet ResNet-18 shared by depth decoder + Siamese pose head (12.8 M), best held-out ATE 0.37 m. Inference adds real per-dataset intrinsics + far-depth clamp + frame-to-frame ICP pose refinement (Open3D). First OWN-model deployment across 8 scenes at 240 frames; superseded by M8.',
    notes_es: 'ResNet-18 de ImageNet compartido por decoder de depth + cabeza de pose Siamese (12.8 M), mejor ATE held-out 0.37 m. La inferencia agrega intrínsecas reales + recorte de profundidad lejana + refinamiento de pose por ICP (Open3D). Primer despliegue del modelo OWN en 8 escenas a 240 frames; reemplazado por M8.',
  },
  {
    id: 'M8', run: 'best recovery run (v0.12.001, LIVE)', backbone: 'resnet18',
    data: 'TUM RGB-D (winning 4-seq subset) + ICL-NUIM, 11k pairs',
    ate: '0.28', deployed: 'live',
    notes_en: 'The best OWN model to date: same ResNet-18 + Siamese architecture, retrained (12 epochs) after experiments confirmed the architectural ceiling. Best held-out ATE 0.28 m (beats M7 0.37 m). Deployed across all 8 OWN scenes with the ICP refinement ladder. Negative results along the way (correlation pose head, more-data-11-seq) are kept in the record; the global-pose-graph (D1) + TSDF stack is implemented and one flag away, awaiting sub-voxel poses.',
    notes_es: 'El mejor modelo OWN hasta ahora: misma arquitectura ResNet-18 + Siamese, reentrenada (12 épocas) tras confirmar el techo arquitectónico. Mejor ATE held-out 0.28 m (supera el 0.37 m de M7). Desplegado en las 8 escenas OWN con el ladder de refinamiento ICP. Los resultados negativos (cabeza de correlación, más-datos-11-seq) quedan en el registro; el stack pose-graph global (D1) + TSDF está implementado a un flag, esperando poses sub-vóxel.',
  },
];
