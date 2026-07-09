import { type Lang } from '../i18n';
import { SubTabs } from '../components/SubTabs';
import { Cite, Refs } from '../components/References';
import { MODEL_HISTORY } from '../data/model_history';

const DEPLOY_LABEL: Record<string, [string, string]> = {
  live: ['LIVE', 'EN VIVO'], 'yes-superseded': ['deployed (superseded)', 'desplegado (reemplazado)'],
  no: ['not deployed', 'no desplegado'], pending: ['pending verify', 'pendiente verificar'],
};

export function Experiments({ lang }: { lang: Lang }) {
  const en = lang === 'en';

  const models = (
    <>
      <h3>{en ? 'Model history (every experiment, nothing lost)' : 'Historial de modelos (cada experimento, sin perder nada)'}</h3>
      <p>{en
        ? 'The complete, honest record of every model trained for the OUR engine: backbone, data, held-out ATE (RMS trajectory error in metres on TUM long-office, Umeyama-aligned; lower is better), whether it was deployed, and every negative result. Kept in sync with the repo docs and the append-only experiments log.'
        : 'El registro completo y honesto de cada modelo entrenado para el motor OUR: backbone, datos, ATE held-out (error RMS de trayectoria en metros en TUM long-office, alineado con Umeyama; menor es mejor), si se desplegó, y cada resultado negativo. Sincronizado con los docs del repo y el log append-only de experimentos.'}</p>
      <table className="data"><thead>
        <tr><th>#</th><th>{en ? 'Run' : 'Corrida'}</th><th>Backbone</th><th>{en ? 'Data' : 'Datos'}</th><th>ATE (m)</th><th>{en ? 'Deployed' : 'Desplegado'}</th><th>{en ? 'Notes' : 'Notas'}</th></tr>
      </thead><tbody>
        {MODEL_HISTORY.map((m) => (
          <tr key={m.id}>
            <td>{m.id}</td><td>{m.run}</td>
            <td><span className="tag">{m.backbone}</span></td>
            <td>{m.data}</td><td>{m.ate}</td>
            <td><span className={'tag' + (m.deployed === 'live' ? ' on' : '')}>{(DEPLOY_LABEL[m.deployed] || ['', ''])[en ? 0 : 1]}</span></td>
            <td className="muted">{en ? m.notes_en : m.notes_es}</td>
          </tr>
        ))}
      </tbody></table>
      <p className="muted">{en
        ? 'The diffuse-vs-sharp look is dominated by pose drift, not depth noise: the per-frame depth is already coherent. Best-checkpoint early stopping helped (M2→M4), extra losses hurt (M5), and the pretrained backbone (M7) is the chosen lever, a stronger encoder plus a steadier Siamese pose head attack the drift directly. Deploy is gated on a verified screenshot comparison, never the ATE number alone.'
        : 'El aspecto difuso-vs-nítido lo domina el drift de pose, no el ruido de depth: la profundidad por cuadro ya es coherente. El early-stopping por mejor checkpoint ayudó (M2→M4), las pérdidas extra dañaron (M5), y el backbone preentrenado (M7) es el lever elegido: un encoder más fuerte más una cabeza de pose Siamese más estable atacan el drift directamente. El despliegue se decide por comparación visual verificada, nunca por el número de ATE solo.'}</p>
    </>
  );

  const cases = (
    <>
      <h3>{en ? 'Cases by category' : 'Casos por categoría'}</h3>
      <ul>
        <li><b>SYN_orbit</b> <span className="tag">{en ? 'synthetic, CPU' : 'sintético, CPU'}</span>: {en ? 'a synthetic procedural corridor (deterministic). A textured tunnel plus a forward camera; it runs in under a second with no GPU or model, exercising the exact pipeline path so CI can smoke-test it.' : 'un corredor procedural sintético (determinista). Un túnel texturizado más una cámara hacia adelante; corre en menos de un segundo sin GPU ni modelo, ejercitando el mismo camino del pipeline para que CI lo testee.'}</li>
        <li><b>LID_synthetic / kitti_lidar</b> <span className="tag">LiDAR</span>: {en ? 'the LiDAR engine (Open3D point-to-plane ICP): synthetic scans (CI-safe) and a real-scan hook for KITTI-style .bin/.npy/.ply.' : 'el motor LiDAR (Open3D ICP punto-a-plano): scans sintéticos (CI-safe) y un hook de scans reales para .bin/.npy/.ply estilo KITTI.'}<Cite k="kissicp" /><Cite k="kitti" /></li>
        <li><b>oxford / university / loop / courthouse</b> <span className="tag">{en ? 'real, GPU' : 'real, GPU'}</span>: {en ? 'real camera sequences baked offline on an 8 GB GPU: an outdoor walk, a courtyard, a revisit (the loop-closure showcase), and a facade orbit.' : 'secuencias reales de cámara horneadas offline en una GPU de 8 GB: una caminata exterior, un patio, un revisit (la vitrina de loop-closure) y una órbita de fachada.'}</li>
        <li><b>OWN_tum_* / OWN_7scenes_* / OWN_icl_living</b> <span className="tag">{en ? 'Track A: RGB-only (Estela)' : 'Track A: solo RGB (Estela)'}</span>: {en ? 'eight real scenes reconstructed by Estela from the RGB stream alone (0.28 m held-out ATE). RGB-only is the hard track: the metric scale must be inferred, and the measured monocular-scale ambiguity is what separates it from Track B.' : 'ocho escenas reales reconstruidas por Estela solo desde el stream RGB (0.28 m ATE held-out). Solo-RGB es el track difícil: la escala métrica debe inferirse, y la ambigüedad de escala monocular medida es lo que lo separa del Track B.'}</li>
        <li><b>RGBD_tum_office / RGBD_tum_desk</b> <span className="tag">{en ? 'Track B: RGB + sensor depth' : 'Track B: RGB + profundidad de sensor'}</span>: {en ? 'the SAME scenes as OWN_tum_office/desk, but integrating the real Kinect depth: SIFT + a depth-edge guard + PnP geometric pose on metric sensor depth + the windowed pose-graph fusion, and a TSDF-denoised surface cloud (0.014-0.040 m after the I1 guard, vs 0.28 m RGB-only). The honest side-by-side of what a depth sensor buys.' : 'las MISMAS escenas que OWN_tum_office/desk, pero integrando la profundidad Kinect real: pose geométrica SIFT + guard de bordes de profundidad + PnP sobre profundidad métrica del sensor + la fusión pose-graph por ventanas, y una nube de superficie denoised por TSDF (0.014-0.040 m tras el guard I1, vs 0.28 m solo-RGB). La comparación honesta de lo que aporta un sensor de profundidad.'}</li>
      </ul>
      <p className="muted">{en ? 'The App replays each case; the Benchmark page reports the numbers per model across cases.' : 'La App reproduce cada caso; la página de Benchmark reporta los números por modelo entre casos.'}</p>
    </>
  );

  const config = (
    <>
      <h3>{en ? 'The 8 GB-safe configuration (measured)' : 'La configuración segura para 8 GB (medida)'}</h3>
      <p>{en
        ? 'On an RTX 4070 Laptop (8 GB), lingbot-map runs with the SDPA attention backend (no FlashInfer build), CPU-offload, a reduced sliding KV window (16), a single camera iteration, bf16, and a frame cap. Verified peak about 7.1 GB. The oxford bake produced a 193k-point RGB cloud over 48 frames with a 3.13 m trajectory.'
        : 'En una RTX 4070 Laptop (8 GB), lingbot-map corre con el backend SDPA (sin compilar FlashInfer), CPU-offload, una ventana KV deslizante reducida (16), una sola iteración de cámara, bf16 y un tope de cuadros. Pico verificado cerca de 7.1 GB. El bake de oxford produjo una nube RGB de 193k puntos sobre 48 cuadros con una trayectoria de 3.13 m.'}<Cite k="flashinfer" /></p>
      <p>{en ? 'This proves the SOTA engine is reachable on modest hardware, which is the precondition for exploring novel ideas on top of it (next tab).' : 'Esto prueba que el motor SOTA es alcanzable en hardware modesto, precondición para explorar ideas novel encima (pestaña siguiente).'}</p>
    </>
  );

  const novel = (
    <>
      <h3>{en ? 'The novel agenda (beyond SOTA)' : 'La agenda novel (más allá del SOTA)'}</h3>
      <p>{en
        ? 'The engine is used as-is; the lab contribution is a set of hypotheses that target lingbot-map documented gaps, each evaluated rigorously, with null results kept. The honest bar is a reproducible reduction of the 7.11 m dense Oxford-Spires ATE from a frozen-backbone add-on.'
        : 'El motor se usa tal cual; el aporte del lab es un conjunto de hipótesis que atacan gaps documentados de lingbot-map, cada una evaluada con rigor, conservando resultados nulos. La barra honesta es una reducción reproducible del ATE denso de 7.11 m en Oxford-Spires desde un add-on de backbone congelado.'}<Cite k="oxfordspires" /></p>
      <table className="data"><thead>
        <tr><th>ID</th><th>{en ? 'Hypothesis' : 'Hipótesis'}</th><th>{en ? 'Method' : 'Método'}</th><th>{en ? 'Status' : 'Estado'}</th></tr>
      </thead><tbody>
        <tr><td>D1</td><td>{en ? 'the frozen trajectory memory already clusters revisited places' : 'la memoria de trayectoria congelada ya agrupa lugares revisitados'}</td><td>{en ? 'dump tokens, test cosine clustering by place, add a contrastive retrieval MLP + an SE(3) pose-graph loop closure' : 'volcar tokens, testear clustering por coseno por lugar, agregar un MLP de retrieval contrastivo + loop closure con pose-graph SE(3)'}</td><td>{en ? 'first experiment' : 'primer experimento'}</td></tr>
        <tr><td>D2</td><td>{en ? 'LiDAR metric depth removes camera scale drift' : 'la profundidad métrica LiDAR quita el drift de escala de cámara'}</td><td>{en ? 'fuse Open3D/KISS-ICP scans with the camera anchor for metric anchoring + drift correction' : 'fusionar scans Open3D/KISS-ICP con el ancla de cámara para anclaje métrico + corrección de drift'}</td><td>{en ? 'proposed' : 'propuesto'}</td></tr>
        <tr><td>D3</td><td>{en ? 'an O(1) recurrent state beats a fixed KV window on long runs' : 'un estado recurrente O(1) supera una ventana KV fija en corridas largas'}</td><td>{en ? 'test-time training / LaCT-style constant-memory recurrence over the token stream' : 'test-time training / recurrencia de memoria constante estilo LaCT sobre el stream de tokens'}</td><td>{en ? 'proposed' : 'propuesto'}</td></tr>
        <tr><td>D4</td><td>{en ? 'a native sparse-LiDAR token stream is a first-class input' : 'un stream de tokens LiDAR sparse nativo es entrada de primera clase'}</td><td>{en ? 'MapAnything/Pi3-style multi-modal token fusion' : 'fusión de tokens multi-modal estilo MapAnything/Pi3'}</td><td>{en ? 'proposed' : 'propuesto'}</td></tr>
        <tr><td>D5</td><td>{en ? 'a DINOv3 backbone lifts geometry for free' : 'un backbone DINOv3 mejora la geometría gratis'}</td><td>{en ? 'drop-in backbone swap, ablate on the dense benchmark' : 'swap directo de backbone, ablación en el benchmark denso'}</td><td>{en ? 'proposed' : 'propuesto'}</td></tr>
      </tbody></table>
      <p className="muted">{en ? 'Each row is a falsifiable claim, adversarially checked before it is believed; a negative result is a valid, recorded outcome.' : 'Cada fila es una afirmación falsable, chequeada adversarialmente antes de creerse; un resultado negativo es un desenlace válido y registrado.'}</p>
    </>
  );

  const honesty = (
    <>
      <h3>{en ? 'Honesty' : 'Honestidad'}</h3>
      <p>{en
        ? 'The bundled example sequences carry no ground-truth poses, so the lab reports trajectory length, point count, and confidence, and explicitly NOT ATE/RPE, which would be faked without ground truth. The synthetic cases are clearly labelled synthetic. Per-case numbers are read from the committed manifests, never from a claim.'
        : 'Las secuencias de ejemplo no traen poses de referencia, así que el lab reporta longitud de trayectoria, cantidad de puntos y confianza, y explícitamente NO ATE/RPE, que serían inventados sin referencia. Los casos sintéticos están etiquetados como sintéticos. Los números por caso se leen de los manifests commiteados, nunca de una afirmación.'}</p>
      <div><span className="tag">7 cases</span> <span className="tag">synthetic control</span> <span className="tag">measured, not claimed</span> <span className="tag">no faked ATE</span></div>
    </>
  );

  return (
    <div className="page">
      <h2>{en ? 'Experiments' : 'Experimentos'}</h2>
      <p className="lead">{en
        ? 'Cases span categories: a synthetic CPU control (the CI smoke test), the LiDAR engine, and real camera sequences baked offline on an 8 GB GPU. This page also lays out the novel agenda evaluated beyond the SOTA engine.'
        : 'Los casos cubren categorías: un control sintético CPU (el smoke de CI), el motor LiDAR y secuencias reales de cámara horneadas offline en una GPU de 8 GB. Esta página también expone la agenda novel evaluada más allá del motor SOTA.'}</p>
      <SubTabs tabs={[
        { id: 'cases', label: en ? 'Cases' : 'Casos', body: <>{cases}<Refs ids={['kissicp', 'kitti']} /></> },
        { id: 'models', label: en ? 'Model history' : 'Historial de modelos', body: <>{models}<Refs ids={['tum', 'iclnuim', 'resnet', 'umeyama']} /></> },
        { id: 'config', label: en ? '8 GB config' : 'Config 8 GB', body: <>{config}<Refs ids={['flashinfer', 'lingbot']} /></> },
        { id: 'novel', label: en ? 'Novel agenda' : 'Agenda novel', body: <>{novel}<Refs ids={['oxfordspires', 'kissicp', 'mapanything', 'dinov3']} /></> },
        { id: 'honesty', label: en ? 'Honesty' : 'Honestidad', body: honesty },
      ]} />
    </div>
  );
}
