import { type Lang } from '../i18n';
import { SubTabs } from '../components/SubTabs';
import { Cite, Refs } from '../components/References';

export function Implementation({ lang }: { lang: Lang }) {
  const en = lang === 'en';

  const pipeline = (
    <>
      <h3>{en ? 'The staged pipeline' : 'El pipeline por etapas'}</h3>
      <p>{en ? 'Run with ' : 'Se ejecuta con '}<code>python -m lidar3dlab.pipeline &lt;case&gt;</code>. {en ? 'The named stages are pure, typed, and seeded; the same case and seed always produce the same artifact.' : 'Las etapas nombradas son puras, tipadas y seeded; el mismo caso y seed siempre producen el mismo artefacto.'}</p>
      <ul>
        <li><code>preprocess</code>: {en ? 'resolve and check the input frames or scans (CONTRACT 1 already validated the schema).' : 'resolver y chequear los cuadros o scans de entrada (CONTRACT 1 ya validó el esquema).'}</li>
        <li><code>feature_extraction</code>: {en ? 'per-frame quality (luma, sharpness) to flag unreliable frames.' : 'calidad por cuadro (luma, nitidez) para marcar cuadros poco fiables.'}</li>
        <li><code>train</code>: {en ? 'active for Estela, our own model: a real local-GPU loop (train_depthpose.py) fits Estela on TUM RGB-D + ICL-NUIM, best-checkpoint early stopping, every epoch logged. Dormant only for the vendored lingbot-map engine (nothing to fit).' : 'activo para Estela, nuestro modelo: un loop real en GPU local (train_depthpose.py) ajusta Estela en TUM RGB-D + ICL-NUIM, early stopping por mejor checkpoint, cada época registrada. Dormido solo para el motor vendorizado lingbot-map (nada que ajustar).'}</li>
        <li><code>infer</code>: {en ? 'dispatch by modality/engine to the synthetic CPU engine (CI-safe), the Estela depth+pose engine, the real lingbot-map GPU engine, or the Open3D LiDAR engine.' : 'despacha por modalidad/motor al motor sintético CPU (CI-safe), al motor Estela de profundidad+pose, al motor real lingbot-map en GPU, o al motor LiDAR Open3D.'}</li>
        <li><code>refine</code>: {en ? 'the texture and color layer: clean the colored cloud and (Open3D) prepare a mesh-ready surface.' : 'la capa de textura y color: limpiar la nube coloreada y (Open3D) preparar una superficie lista para malla.'}<Cite k="open3d" /></li>
        <li><code>evaluate</code>: {en ? 'trajectory and cloud metrics (ATE/RPE only when ground-truth poses exist).' : 'métricas de trayectoria y nube (ATE/RPE solo si hay poses de referencia).'}</li>
        <li><code>export</code>: {en ? 'the compact artifact and manifest (CONTRACT 2), with the frame_offsets for the web replay.' : 'el artefacto compacto y manifest (CONTRACT 2), con los frame_offsets para el replay web.'}</li>
      </ul>
    </>
  );

  const ownpipe = (
    <>
      <h3>{en ? 'Our model: train -> checkpoint -> engine -> bake -> serve' : 'Nuestro modelo: entrenar -> checkpoint -> engine -> precomputar -> servir'}</h3>
      <p>{en ? 'Our own depth+pose model is a real, reproducible local-GPU pipeline, not a mock:' : 'El modelo propio de profundidad+pose es un pipeline real y reproducible en GPU local, no un mock:'}</p>
      <ul>
        <li><b>{en ? 'Train' : 'Entrenar'}:</b> <code>train_depthpose.py --backbone resnet18 --use_icl</code> {en ? 'fits the net on real TUM RGB-D (11 sequences) + ICL-NUIM perfect-depth. Aleatoric depth NLL + se(3) pose loss, best-checkpoint early stopping. long_office is held out for the ATE.' : 'ajusta la red en TUM RGB-D real (11 secuencias) + ICL-NUIM de profundidad perfecta. NLL de profundidad aleatoria + pérdida de pose se(3), early stopping por mejor checkpoint. long_office queda held-out para el ATE.'}</li>
        <li><b>{en ? 'Checkpoint' : 'Checkpoint'}:</b> {en ? 'a per-backbone archive (own-depthpose-<backbone>.pt) + the canonical file + a tiny meta sidecar (backbone, ATE, data) that the pipeline reads for an accurate engine label. Every epoch is appended to experiments.jsonl (nothing lost).' : 'un archivo por-backbone (own-depthpose-<backbone>.pt) + el canónico + un pequeño sidecar meta (backbone, ATE, datos) que el pipeline lee para un label preciso. Cada época se anexa a experiments.jsonl (sin perder nada).'}</li>
        <li><b>{en ? 'Engine' : 'Motor'}:</b> {en ? 'own_engine runs the model over the ordered RGB frames (real per-dataset intrinsics), then the pose-refinement ladder (ICP, optionally global pose-graph / TSDF), then unprojects into a fused RGB cloud.' : 'own_engine ejecuta el modelo sobre los cuadros RGB ordenados (intrínsecas reales por dataset), luego el ladder de refinamiento de pose (ICP, opcionalmente pose-graph global / TSDF), y desproyecta en una nube RGB fusionada.'}<Cite k="open3d" /></li>
        <li><b>{en ? 'Bake + serve' : 'Precomputar + servir'}:</b> {en ? 'the compact trace (CONTRACT 2) + a committed Potree octree; the static site replays them. Weights stay off-git (LIDAR3D_MODELS_ROOT); only the small experiment ledger is versioned.' : 'el trace compacto (CONTRACT 2) + un octree Potree confirmado; el sitio estático los reproduce. Los pesos quedan fuera de git (LIDAR3D_MODELS_ROOT); solo el pequeño ledger de experimentos se versiona.'}</li>
      </ul>
      <p className="muted">{en ? 'The model is agnostic behind one reconstruct(spec) -> ReconResult contract, so control / classical / SOTA-reference / ours engines are directly comparable. Add a case by pointing the engine at any folder of ordered RGB frames.' : 'El modelo es agnóstico tras un contrato reconstruct(spec) -> ReconResult, así los motores control / clásico / referencia-SOTA / nuestro son directamente comparables. Agregar un caso = apuntar el motor a cualquier carpeta de cuadros RGB ordenados.'}</p>
    </>
  );

  const contracts = (
    <>
      <h3>{en ? 'The two data contracts' : 'Los dos contratos de datos'}</h3>
      <p><b>{en ? 'Ingestion (raw to pipeline)' : 'Ingesta (raw a pipeline)'}:</b> {en ? 'a bring-your-own-data gate that accepts a sequence only if it satisfies the RGB-sequence schema (frame count, size, format) and an explicit outlier policy; bad inputs are rejected with a reason, never coerced.' : 'una puerta bring-your-own-data que acepta una secuencia solo si cumple el esquema RGB (cantidad de cuadros, tamaño, formato) y una política de outliers explícita; entradas malas se rechazan con razón, nunca se fuerzan.'}</p>
      <p><b>{en ? 'Artifact (pipeline to web)' : 'Artefacto (pipeline a web)'}:</b> {en ? 'every run writes a compact base64 colored-cloud trace and a manifest (params, seed, the lane/gate verdict, byte size). The TypeScript types mirror it, so a contract drift fails the web build. No absolute path is ever written.' : 'cada corrida escribe un trace compacto base64 de nube coloreada y un manifest (params, seed, el veredicto de lane/gate, tamaño). Los tipos TypeScript lo reflejan, así un drift rompe el build. Nunca se escribe una ruta absoluta.'}</p>
      <p className="muted">{en ? 'This is why the App cannot ship reading a shape the pipeline does not produce: the contract is enforced at build time.' : 'Por eso la App no puede publicarse leyendo una forma que el pipeline no produce: el contrato se aplica en tiempo de build.'}</p>
    </>
  );

  const gate = (
    <>
      <h3>{en ? 'The lane gate' : 'El gate de lane'}</h3>
      <p>{en
        ? 'A measured gate (ADR-0054) classifies each case into a lane. It checks whether the run is pure-Python and Pyodide-safe, and measures the artifact byte size and run time against budgets. Because the engine needs torch and a GPU (and matplotlib for depth thumbnails), every case classifies as precompute: the browser never recomputes, it replays a committed artifact.'
        : 'Un gate medido (ADR-0054) clasifica cada caso en un lane. Verifica si la corrida es pure-Python y Pyodide-safe, y mide el tamaño del artefacto y el tiempo contra presupuestos. Como el motor necesita torch y una GPU (y matplotlib para los thumbnails de profundidad), cada caso clasifica como precompute: el browser nunca recomputa, reproduce un artefacto confirmado.'}</p>
      <p>{en ? 'The gate verdict (lane, budgets, reasons) is stored in the manifest and surfaced in the App stats, so the separation is auditable, not just asserted.' : 'El veredicto del gate (lane, presupuestos, razones) se guarda en el manifest y se muestra en las stats de la App, así la separación es auditable, no solo afirmada.'}</p>
    </>
  );

  const envtab = (
    <>
      <h3>{en ? 'Environment and secrets' : 'Entorno y secretos'}</h3>
      <p>{en ? 'Heavy weights (about 14 GB) and footage live outside git on a scratch volume, resolved by environment variables (LIDAR3D_MODELS_ROOT, LIDAR3D_DATA_ROOT); the real values come from a gitignored .env provisioned from the credentials vault. No personal path is ever committed, and the API never returns an absolute path.' : 'Los pesos (unos 14 GB) y el video viven fuera de git en un volumen scratch, resueltos por variables de entorno (LIDAR3D_MODELS_ROOT, LIDAR3D_DATA_ROOT); los valores reales vienen de un .env ignorado por git provisto del vault de credenciales. Ninguna ruta personal se versiona en git, y la API nunca devuelve una ruta absoluta.'}</p>
      <p>{en ? 'The Python engine runs in an isolated .venv (never global) and the frontend in a local node_modules; the two toolchains stay separate.' : 'El motor Python se ejecuta en un .venv aislado (nunca global) y el frontend en un node_modules local; las dos toolchains quedan separadas.'}</p>
      <div><span className="tag">isolated .venv</span> <span className="tag">staged pipeline</span> <span className="tag">2 contracts</span> <span className="tag">lane gate</span> <span className="tag">env-from-vault</span></div>
    </>
  );

  return (
    <div className="page">
      <h2>{en ? 'Implementation' : 'Implementación'}</h2>
      <p className="lead">{en
        ? 'The repo is instantiated from the CAOS product template (ADR-0057): a frozen base with a named staged pipeline, two enforced data contracts, a measured lane gate, and a static replay frontend. Rework lives only in the core (the engine, the visuals, the cases).'
        : 'El repo se instancia del template de producto CAOS (ADR-0057): una base congelada con un pipeline por etapas, dos contratos de datos, un gate de lane medido y un frontend de replay estático. El trabajo vive solo en el core (el motor, los visuales, los casos).'}</p>
      <SubTabs tabs={[
        { id: 'pipe', label: en ? 'Staged pipeline' : 'Pipeline por etapas', body: <>{pipeline}<Refs ids={['open3d', 'lingbot', 'kissicp']} /></> },
        { id: 'ownpipe', label: en ? 'Our model pipeline' : 'Pipeline de nuestro modelo', body: <>{ownpipe}<Refs ids={['open3d', 'tum', 'iclnuim']} /></> },
        { id: 'contracts', label: en ? 'Data contracts' : 'Contratos de datos', body: contracts },
        { id: 'gate', label: en ? 'Lane gate' : 'Gate de lane', body: gate },
        { id: 'env', label: en ? 'Environment' : 'Entorno', body: envtab },
      ]} />
    </div>
  );
}
