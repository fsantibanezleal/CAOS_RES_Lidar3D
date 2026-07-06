// Minimal EN/ES i18n (English default, ADR-0011). Chrome + key labels are bilingual; the deep technical
// page prose is English (code/docs language) with bilingual headings.
export type Lang = 'en' | 'es';

export const DICT: Record<string, { en: string; es: string }> = {
  tagline: { en: 'Streaming 3D reconstruction lab', es: 'Lab de reconstrucción 3D en streaming' },
  nav_app: { en: 'App', es: 'App' },
  nav_intro: { en: 'Introduction', es: 'Introducción' },
  nav_method: { en: 'Methodology', es: 'Metodología' },
  nav_impl: { en: 'Implementation', es: 'Implementación' },
  nav_exp: { en: 'Experiments', es: 'Experimentos' },
  nav_bench: { en: 'Benchmark', es: 'Benchmark' },
  arch: { en: 'Architecture', es: 'Arquitectura' },
  source: { en: 'Source / case', es: 'Fuente / caso' },
  point_size: { en: 'Point size', es: 'Tamaño de punto' },
  fit: { en: 'Fit view', es: 'Encuadrar' },
  live_depth: { en: 'Per-frame depth', es: 'Profundidad por cuadro' },
  stats: { en: 'Reconstruction stats', es: 'Métricas de reconstrucción' },
  engine: { en: 'Engine', es: 'Motor' },
  frames: { en: 'Frames', es: 'Cuadros' },
  points: { en: 'Points', es: 'Puntos' },
  path: { en: 'Path length', es: 'Longitud trayecto' },
  lane: { en: 'Lane', es: 'Lane' },
  refine: { en: 'Refine', es: 'Refinado' },
  category: { en: 'Category', es: 'Categoría' },
  expected: { en: 'Expected', es: 'Esperado' },
  replay_note: {
    en: 'Replaying a committed artifact (CONTRACT 2): a real reconstruction baked offline by the selected engine, not a live demo. For your own footage run the local-GPU API: uvicorn app.main:app, then POST /api/live/reconstruct (see the README).',
    es: 'Reproduciendo un artefacto commiteado (CONTRACT 2): una reconstrucción real horneada offline por el motor seleccionado, no un demo en vivo. Para tu propio video corre la API GPU local: uvicorn app.main:app y POST /api/live/reconstruct (ver README).',
  },
  close: { en: 'Close', es: 'Cerrar' },
};

export const t = (lang: Lang, key: string): string => DICT[key]?.[lang] ?? key;
