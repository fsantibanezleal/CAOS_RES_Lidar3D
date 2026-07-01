import { type Lang } from '../i18n';
import { Katex } from '../components/Katex';
import { SubTabs } from '../components/SubTabs';
import { ContextDiagram, GCTDiagram } from '../components/Diagrams';
import { Cite, Refs } from '../components/References';

export function Methodology({ lang }: { lang: Lang }) {
  const en = lang === 'en';

  const sota = (
    <>
      <h3>{en ? 'From per-scene optimization to a single forward pass' : 'De optimización por escena a un solo forward'}</h3>
      <p>{en
        ? 'Classical visual SLAM (ORB-SLAM3, DROID-SLAM) and LiDAR odometry (LOAM, KISS-ICP) recover geometry by optimizing: extract features, match them, and minimize a reprojection or point-to-plane residual over a pose graph. It is accurate but iterative, sensitive to initialization, and hard to run causally at frame rate on long sequences.'
        : 'El SLAM visual clásico (ORB-SLAM3, DROID-SLAM) y la odometría LiDAR (LOAM, KISS-ICP) recuperan geometría optimizando: extraer features, emparejarlos y minimizar un residual de reproyección o punto-a-plano sobre un grafo de poses. Es preciso pero iterativo, sensible a la inicialización y difícil de correr causalmente a frame rate en secuencias largas.'}<Cite k="orbslam3" /><Cite k="droid" /><Cite k="kissicp" /></p>
      <p>{en
        ? 'DUSt3R reframed the problem: a transformer regresses a dense pointmap for an image pair directly, no correspondences, no bundle adjustment. MASt3R added metric matching, and VGGT scaled it to many views in one pass with alternating frame / global attention. lingbot-map is the streaming heir: it keeps VGGT-style attention but drives it causally with a bounded memory, so it reconstructs a live video instead of a fixed image set.'
        : 'DUSt3R reformuló el problema: un transformer regresa directamente un pointmap denso para un par de imágenes, sin correspondencias ni bundle adjustment. MASt3R agregó matching métrico, y VGGT lo escaló a muchas vistas en una pasada con atención alternada por-cuadro / global. lingbot-map es el heredero en streaming: mantiene la atención estilo VGGT pero la ejecuta causalmente con memoria acotada, reconstruyendo un video en vivo en vez de un set fijo de imágenes.'}<Cite k="dust3r" /><Cite k="mast3r" /><Cite k="vggt" /><Cite k="lingbot" /></p>

      <h3>{en ? 'The feed-forward 3D lineage' : 'El linaje 3D feed-forward'}</h3>
      <table className="data"><thead>
        <tr><th>{en ? 'Method' : 'Método'}</th><th>{en ? 'Input' : 'Entrada'}</th><th>{en ? 'What it added' : 'Qué aportó'}</th></tr>
      </thead><tbody>
        <tr><td>DUSt3R <Cite k="dust3r" /></td><td>{en ? 'image pair' : 'par de imágenes'}</td><td>{en ? 'direct pointmap regression, no correspondences' : 'regresión directa de pointmap, sin correspondencias'}</td></tr>
        <tr><td>MASt3R <Cite k="mast3r" /></td><td>{en ? 'image pair' : 'par de imágenes'}</td><td>{en ? 'metric-scale matching head' : 'cabeza de matching a escala métrica'}</td></tr>
        <tr><td>Spann3R / CUT3R <Cite k="spann3r" /><Cite k="cut3r" /></td><td>{en ? 'stream' : 'stream'}</td><td>{en ? 'a persistent spatial memory / recurrent state' : 'memoria espacial persistente / estado recurrente'}</td></tr>
        <tr><td>VGGT <Cite k="vggt" /></td><td>N {en ? 'views' : 'vistas'}</td><td>{en ? 'alternating frame/global attention, one pass' : 'atención alternada cuadro/global, una pasada'}</td></tr>
        <tr><td><b>lingbot-map</b> <Cite k="lingbot" /></td><td>{en ? 'live video' : 'video en vivo'}</td><td>{en ? 'causal streaming + bounded Geometric Context' : 'streaming causal + Contexto Geométrico acotado'}</td></tr>
      </tbody></table>
      <p className="muted">{en
        ? 'This lab uses lingbot-map as-is for the camera engine and Open3D point-to-plane ICP (KISS-ICP swappable) for the LiDAR engine; the Experiments page is where the novel proposals beyond this SOTA are evaluated.'
        : 'Este lab usa lingbot-map tal cual para el motor de cámara y Open3D ICP punto-a-plano (KISS-ICP intercambiable) para el motor LiDAR; la página de Experimentos evalúa las propuestas novel más allá de este SOTA.'}</p>
    </>
  );

  const networks = (
    <>
      <h3>{en ? 'The Geometric Context Transformer (GCT)' : 'El Geometric Context Transformer (GCT)'}</h3>
      <p>{en
        ? 'Each frame is encoded by a frozen DINOv2 ViT (patch-14) into patch tokens, then processed by 24 blocks that alternate frame attention (within one frame) and cross-frame attention (across the context). Three lightweight heads read the final tokens: a pose head, a dense metric-depth head, and a confidence head. The backbone is frozen, so training touches only the geometric blocks and heads.'
        : 'Cada cuadro se codifica con un DINOv2 ViT congelado (patch-14) en tokens de parche, y luego pasa por 24 bloques que alternan atención por-cuadro (dentro de un cuadro) y entre-cuadros (a lo largo del contexto). Tres cabezas livianas leen los tokens finales: una de pose, una de profundidad métrica densa y una de confianza. El backbone está congelado, así que el entrenamiento toca solo los bloques geométricos y las cabezas.'}<Cite k="dinov2" /><Cite k="vggt" /></p>
      <GCTDiagram lang={lang} />
      <ul>
        <li><b>DINOv2 <Cite k="dinov2" />:</b> {en ? 'a self-supervised ViT whose features are semantically and geometrically rich; used frozen as the per-frame tokenizer (DINOv3 is a drop-in upgrade path studied in Experiments).' : 'un ViT auto-supervisado con features semántica y geométricamente ricas; usado congelado como tokenizador por-cuadro (DINOv3 es una ruta de upgrade directa estudiada en Experimentos).'}<Cite k="dinov3" /></li>
        <li><b>{en ? 'Alternating attention' : 'Atención alternada'} <Cite k="vggt" />:</b> {en ? 'frame blocks give intra-frame geometry; cross-frame blocks fuse the temporal context. This is the VGGT design, made causal.' : 'los bloques por-cuadro dan geometría intra-cuadro; los entre-cuadros fusionan el contexto temporal. Es el diseño de VGGT, hecho causal.'}</li>
        <li><b>{en ? 'Heads' : 'Cabezas'}:</b> {en ? 'pose (a compact absT·quatR·FoV encoding), dense metric depth, and per-pixel confidence used to filter the cloud.' : 'pose (codificación compacta absT·quatR·FoV), profundidad métrica densa y confianza por píxel para filtrar la nube.'}</li>
      </ul>
      <p className="muted">{en ? 'Note: the model emits pose + depth + confidence, not world points. The lab unprojects depth itself (see Geometry).' : 'Nota: el modelo emite pose + profundidad + confianza, no puntos de mundo. El lab desproyecta la profundidad (ver Geometría).'}</p>
    </>
  );

  const context = (
    <>
      <h3>Geometric Context Attention</h3>
      <p>{en ? 'A causal stream cannot attend to all past frames, and it cannot forget them either. The GCT solves this with three attention contexts, each targeting a distinct SLAM failure mode:' : 'Un stream causal no puede atender a todos los cuadros pasados, ni tampoco olvidarlos. El GCT lo resuelve con tres contextos de atención, cada uno atacando un modo de falla de SLAM:'}</p>
      <ul>
        <li><b>{en ? 'Anchor context' : 'Contexto ancla'}:</b> {en ? 'the first n frames (full attention plus a learnable token) fix the world frame and the metric scale, set from the anchor cloud as ' : 'los primeros n cuadros (atención completa más un token aprendible) fijan el marco de mundo y la escala métrica, definida desde la nube ancla como '}<Katex tex={String.raw`s=\tfrac{1}{|\mathcal{X}|}\sum\|\mathbf{x}\|_2`} />.</li>
        <li><b>{en ? 'Pose-reference window' : 'Ventana de pose'}:</b> {en ? 'the k≈16–64 most recent frames at full token resolution give dense local geometry for accurate relative pose.' : 'los k≈16–64 cuadros recientes a resolución completa dan geometría local densa para pose relativa precisa.'}</li>
        <li><b>{en ? 'Trajectory memory' : 'Memoria de trayectoria'}:</b> {en ? 'all older frames are compressed to 6 tokens each (ordered by Video-RoPE) for cheap long-range drift correction.' : 'todos los cuadros viejos se comprimen a 6 tokens cada uno (ordenados por Video-RoPE) para corregir drift de largo rango barato.'}<Cite k="rope" /></li>
      </ul>
      <ContextDiagram lang={lang} />
      <p>{en ? 'The per-frame context is therefore ' : 'El contexto por cuadro es entonces '}<Katex tex={String.raw`(n+k)\,M + 6T`} />{en ? ' tokens (a constant part plus a tiny linear part) versus ' : ' tokens (una parte constante más una parte lineal diminuta) versus '}<Katex tex={String.raw`M\,T`} />{en ? ' for naive causal attention, about an 80x reduction over 10k frames, which is what makes streaming at roughly 20 FPS feasible. The key/value tensors live in a paged KV cache (FlashInfer, with an SDPA fallback for 8 GB cards).' : ' para atención causal naive, cerca de 80x menos sobre 10k cuadros, que es lo que hace factible el streaming a ~20 FPS. Los tensores key/value viven en un KV cache paginado (FlashInfer, con fallback SDPA para tarjetas de 8 GB).'}<Cite k="flashinfer" /></p>
    </>
  );

  const geometry = (
    <>
      <h3>{en ? 'Pose encoding and SE(3)' : 'Codificación de pose y SE(3)'}</h3>
      <p>{en ? 'The pose head emits a compact encoding: an absolute translation, a quaternion rotation, and a field of view (absT·quatR·FoV). The quaternion is normalized and mapped to a rotation matrix; together with the translation it forms the camera-to-world transform ' : 'La cabeza de pose emite una codificación compacta: traslación absoluta, rotación por cuaternión y campo de visión (absT·quatR·FoV). El cuaternión se normaliza y se mapea a matriz de rotación; junto con la traslación forma la transformada cámara-a-mundo '}<Katex tex={String.raw`\mathbf{P}_{c2w}=\begin{bmatrix}\mathbf{R}&\mathbf{t}\\\mathbf{0}&1\end{bmatrix}\in SE(3)`} />.</p>

      <h3>{en ? 'Depth to a colored world cloud' : 'De profundidad a nube de mundo coloreada'}</h3>
      <p>{en ? 'The FoV self-calibrates the intrinsics (' : 'El FoV auto-calibra los intrínsecos ('}<Katex tex={String.raw`f_x=\tfrac{W}{2}\cot\tfrac{\theta}{2}`} />{en ? '). Each pixel with depth D is back-projected through the pinhole model and mapped to the world frame; each point takes the color of its source pixel and is kept only if its confidence passes a quantile threshold:' : '). Cada píxel con profundidad D se retro-proyecta por el modelo pinhole y se lleva al marco de mundo; cada punto toma el color de su píxel fuente y se conserva solo si su confianza supera un umbral por cuantil:'}</p>
      <Katex block tex={String.raw`\mathbf{X}^{(t)}_{world} = \mathbf{P}^{(t)}_{c2w}\begin{bmatrix}\frac{u-c_x}{f_x}\,D\\[2pt]\frac{v-c_y}{f_y}\,D\\[2pt]D\\[2pt]1\end{bmatrix},\qquad \text{keep if } \sigma(u,v)\ge \tau_q`} />
      <p>{en ? 'Concatenating the kept points over all frames gives the RGB world cloud you replay in the App; the per-frame counts are stored as ' : 'Concatenar los puntos conservados sobre todos los cuadros da la nube RGB de mundo que reproduces en la App; los conteos por cuadro se guardan como '}<Katex tex={String.raw`\text{frame\_offsets}`} />{en ? ' so the web can reveal the reconstruction in exact frame order.' : ' para que la web revele la reconstrucción en orden exacto de cuadro.'}</p>

      <h3>{en ? 'The LiDAR engine' : 'El motor LiDAR'}</h3>
      <p>{en ? 'For LiDAR sequences the lab registers consecutive scans with point-to-plane ICP, minimizing ' : 'Para secuencias LiDAR el lab registra scans consecutivos con ICP punto-a-plano, minimizando '}<Katex tex={String.raw`\sum_i\big((\mathbf{R}\mathbf{p}_i+\mathbf{t}-\mathbf{q}_i)\cdot \mathbf{n}_i\big)^2`} />{en ? ' and accumulating a height-colored map plus the trajectory. KISS-ICP is pinned and swappable behind the same interface.' : ' y acumulando un mapa coloreado por altura más la trayectoria. KISS-ICP queda fijado e intercambiable tras la misma interfaz.'}<Cite k="kissicp" /><Cite k="open3d" /></p>
    </>
  );

  return (
    <div className="page">
      <h2>{en ? 'Methodology' : 'Metodología'}</h2>
      <p className="lead">{en
        ? 'The camera engine is the Geometric Context Transformer (GCT): a frozen-DINOv2 ViT with 24 alternating frame / cross-frame attention blocks, driven causally with a three-tier context and a paged KV cache. This page covers the state of the art, the networks, the attention context, and the geometry.'
        : 'El motor de cámara es el Geometric Context Transformer (GCT): un ViT con DINOv2 congelado y 24 bloques alternados de atención por-cuadro / entre-cuadros, ejecutado causalmente con un contexto de tres niveles y un KV cache paginado. Esta página cubre el estado del arte, las redes, el contexto de atención y la geometría.'}</p>
      <SubTabs tabs={[
        { id: 'sota', label: en ? 'State of the art' : 'Estado del arte', body: <>{sota}<Refs ids={['dust3r', 'mast3r', 'vggt', 'lingbot', 'spann3r', 'cut3r', 'orbslam3', 'droid', 'kissicp']} /></> },
        { id: 'net', label: en ? 'Networks' : 'Redes', body: <>{networks}<Refs ids={['dinov2', 'dinov3', 'vggt', 'lingbot']} /></> },
        { id: 'ctx', label: en ? 'Geometric Context' : 'Contexto Geométrico', body: <>{context}<Refs ids={['lingbot', 'rope', 'flashinfer', 'vggt']} /></> },
        { id: 'geo', label: en ? 'Geometry' : 'Geometría', body: <>{geometry}<Refs ids={['lingbot', 'kissicp', 'open3d']} /></> },
      ]} />
    </div>
  );
}
