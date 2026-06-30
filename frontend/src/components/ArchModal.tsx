import { type Lang } from '../i18n';

// ADR-0058: the in-app "how it was built" architecture modal. Three lanes + the data-flow, themed.
export function ArchModal({ lang, onClose }: { lang: Lang; onClose: () => void }) {
  const en = lang === 'en';
  return (
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="card">
        <div className="card-h">
          <b>{en ? 'How it works' : 'Cómo funciona'}</b>
          <button className="primary" onClick={onClose}>{en ? 'Close' : 'Cerrar'}</button>
        </div>
        <div className="card-b">
          <p>{en
            ? 'lingbot-map (arXiv:2604.14141) is a feed-forward Geometric Context Transformer that turns a video stream into camera poses + dense metric depth, frame by frame, with no per-scene optimization. This product has three lanes (ADR-0057):'
            : 'lingbot-map (arXiv:2604.14141) es un Geometric Context Transformer feed-forward que convierte un stream de video en poses de cámara + profundidad métrica densa, cuadro a cuadro, sin optimización por escena. Este producto tiene tres lanes (ADR-0057):'}</p>
          <pre className="diagram">{`  OFFLINE (precompute, GPU)        REPLAY (this web, static)        LIVE (local-GPU API, dormant)
  ─────────────────────────        ─────────────────────────        ─────────────────────────────
  lidar3dlab/stages:               frontend/ loads the committed     app/ (FastAPI) streams a fresh
  preprocess → infer(lingbot)      artifact + manifest (CONTRACT 2)  reconstruction over WebSocket
  → refine(color/texture)          and replays the RGB point cloud   on a machine with the GPU +
  → evaluate → export  ──────────► + camera trajectory in three.js   the 4.6 GB checkpoint
       │                                  ▲                                  (not browser-feasible:
       ▼                                  │                                   a 1B-param ViT)
  data/derived/<case>/trace.json ─────────┘  (no recompute in the browser)`}</pre>
          <ul>
            <li><b>{en ? 'Offline lane' : 'Lane offline'}:</b> {en
              ? 'the heavy lingbot-map model runs on a GPU and bakes a committed, RGB-colored point-cloud artifact + a manifest (the two enforced data contracts).'
              : 'el modelo pesado lingbot-map corre en GPU y hornea un artefacto de nube de puntos RGB + un manifest (los dos contratos de datos).'}</li>
            <li><b>{en ? 'Replay lane (here)' : 'Lane replay (aquí)'}:</b> {en
              ? 'this static site loads ONLY committed artifacts and replays them; it never recomputes. That is what you see in the App.'
              : 'este sitio estático carga SOLO artefactos commiteados y los reproduce; nunca recomputa. Es lo que ves en la App.'}</li>
            <li><b>{en ? 'Live lane' : 'Lane live'}:</b> {en
              ? 'real-time reconstruction of your own footage runs on a local GPU via the dormant app/ API (the model is too heavy for the browser).'
              : 'la reconstrucción en vivo de tu propio video corre en GPU local vía la API app/ (el modelo es demasiado pesado para el browser).'}</li>
          </ul>
          <p className="refs">{en ? 'Both data contracts are enforced: the ingestion gate (RGB-sequence schema) and the artifact manifest mirrored by the TypeScript types (a drift fails the build).'
            : 'Ambos contratos se aplican: la puerta de ingesta (esquema de secuencia RGB) y el manifest del artefacto espejado por los tipos TypeScript (un drift rompe el build).'}</p>
        </div>
      </div>
    </div>
  );
}
