import { type Lang } from '../i18n';

export function Implementation({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <div className="page">
      <h2>{en ? 'Implementation' : 'Implementación'}</h2>
      <p className="lead">{en
        ? 'The repo is instantiated from the CAOS product template (ADR-0057): a frozen base with a named staged pipeline, two enforced data contracts, a measured lane gate, and a static replay frontend. Rework lives only in the core (the engine, the visuals, the cases).'
        : 'El repo se instancia del template de producto CAOS (ADR-0057): una base congelada con un pipeline por etapas, dos contratos de datos, un gate de lane medido y un frontend de replay estático. El trabajo vive solo en el core (el motor, los visuales, los casos).'}</p>

      <h3>{en ? 'The staged pipeline' : 'El pipeline por etapas'}</h3>
      <p>{en ? 'Run with ' : 'Se corre con '}<code>python -m lidar3dlab.pipeline &lt;case&gt;</code>. {en ? 'The named stages are pure, typed and seeded:' : 'Las etapas nombradas son puras, tipadas y seeded:'}</p>
      <ul>
        <li><code>preprocess</code> — {en ? 'resolve + check the RGB frames (CONTRACT 1 already validated the schema).' : 'resolver + chequear los cuadros RGB (CONTRACT 1 ya validó el esquema).'}</li>
        <li><code>feature_extraction</code> — {en ? 'per-frame quality (luma, sharpness) to flag unreliable frames.' : 'calidad por cuadro (luma, nitidez) para marcar cuadros poco fiables.'}</li>
        <li><code>train</code> — {en ? 'dormant: the engine is the pretrained lingbot-map (no surrogate to fit).' : 'dormido: el motor es lingbot-map pre-entrenado (no hay surrogate que ajustar).'}</li>
        <li><code>infer</code> — {en ? 'dispatch to the synthetic CPU engine (CI-safe) or the real lingbot-map GPU engine.' : 'despacha al motor sintético CPU (CI-safe) o al motor real lingbot-map en GPU.'}</li>
        <li><code>refine</code> — {en ? 'the texture/color layer: clean the colored cloud + (Open3D) a mesh-ready surface.' : 'la capa de textura/color: limpiar la nube coloreada + (Open3D) una superficie lista para malla.'}</li>
        <li><code>evaluate</code> — {en ? 'trajectory + cloud metrics (ATE/RPE only when ground-truth poses exist).' : 'métricas de trayectoria + nube (ATE/RPE solo si hay poses de referencia).'}</li>
        <li><code>export</code> — {en ? 'the compact artifact + manifest (CONTRACT 2).' : 'el artefacto compacto + manifest (CONTRACT 2).'}</li>
      </ul>

      <h3>{en ? 'The two data contracts' : 'Los dos contratos de datos'}</h3>
      <p><b>{en ? 'Ingestion (raw → pipeline)' : 'Ingesta (raw → pipeline)'}:</b> {en ? 'a bring-your-own-data gate that accepts a sequence iff it satisfies the RGB-sequence schema (frame count, size, format) and an explicit outlier policy; bad inputs are rejected with a reason, never coerced.' : 'una puerta bring-your-own-data que acepta una secuencia si cumple el esquema RGB (cantidad de cuadros, tamaño, formato) y una política de outliers explícita; entradas malas se rechazan con razón, nunca se fuerzan.'}</p>
      <p><b>{en ? 'Artifact (pipeline → web)' : 'Artefacto (pipeline → web)'}:</b> {en ? 'every run writes a compact base64 colored-cloud trace + a manifest (params, seed, the lane/gate verdict, byte size). The TypeScript types mirror it, so a contract drift fails the web build. No absolute paths are ever written.' : 'cada corrida escribe un trace compacto base64 de nube coloreada + un manifest (params, seed, el veredicto de lane/gate, tamaño). Los tipos TypeScript lo espejan, así un drift rompe el build. Nunca se escriben rutas absolutas.'}</p>

      <h3>{en ? 'Environment + secrets' : 'Entorno + secretos'}</h3>
      <p>{en ? 'Heavy weights (~14 GB) and footage live outside git on a scratch volume, resolved by environment variables; the real values come from a gitignored .env provisioned from the credentials vault. No personal path is ever committed, and the API never returns an absolute path.' : 'Los pesos (~14 GB) y el video viven fuera de git en un volumen scratch, resueltos por variables de entorno; los valores reales vienen de un .env gitignoreado provisto del vault de credenciales. Ninguna ruta personal se commitea, y la API nunca devuelve una ruta absoluta.'}</p>
      <div><span className="tag">two-venv</span><span className="tag">staged pipeline</span><span className="tag">2 contracts</span><span className="tag">lane gate</span><span className="tag">env-from-vault</span></div>
    </div>
  );
}
