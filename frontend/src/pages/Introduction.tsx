import { type Lang } from '../i18n';
import { Katex } from '../components/Katex';
import { SubTabs } from '../components/SubTabs';
import { Cite, Refs } from '../components/References';

export function Introduction({ lang }: { lang: Lang }) {
  const en = lang === 'en';

  const overview = (
    <>
      <h3>{en ? 'The problem' : 'El problema'}</h3>
      <p>{en
        ? 'Streaming 3D reconstruction recovers, at each incoming frame t and using only the current and past frames, the absolute camera pose, a dense depth map, and (by reprojection) a point cloud, with geometric accuracy, temporal consistency, and bounded compute. Classically this is SLAM: tracking, mapping, and bundle adjustment. The frontier replaces that per-scene optimization with a single transformer forward pass.'
        : 'La reconstrucción 3D en streaming recupera, en cada cuadro t y usando solo el cuadro actual y los pasados, la pose absoluta de cámara, un mapa de profundidad denso y (por reproyección) una nube de puntos, con precisión geométrica, consistencia temporal y cómputo acotado. Clásicamente esto es SLAM: tracking, mapping y bundle adjustment. La frontera reemplaza esa optimización por escena con un solo forward de un transformer.'}</p>
      <p>{en ? 'A pointmap is a per-pixel 3D position in a common frame; given a depth map D and intrinsics K, a pixel (u,v) unprojects to a camera-frame point and then to the world via the camera-to-world pose:' : 'Un pointmap es una posición 3D por píxel en un marco común; dada una profundidad D e intrínsecos K, un píxel (u,v) se desproyecta a un punto en el marco de cámara y luego al mundo vía la pose cámara-a-mundo:'}</p>
      <Katex block tex={String.raw`\mathbf{X}_{world} = \mathbf{R}_{c2w}\,\underbrace{D(u,v)\,\mathbf{K}^{-1}[u,v,1]^\top}_{\text{camera-frame point}} + \mathbf{t}_{c2w}`} />
      <div>
        <span className="tag">feed-forward</span> <span className="tag">streaming SLAM</span> <span className="tag">pointmap</span> <span className="tag sota">Apache-2.0 engine</span>
      </div>
    </>
  );

  const lineage = (
    <>
      <h3>{en ? 'The state of the art (the lineage)' : 'El estado del arte (el linaje)'}</h3>
      <p>{en
        ? 'Feed-forward pointmap models regress geometry directly from pixels. The lineage runs DUSt3R (2023), then MASt3R, then VGGT (CVPR 2025 best paper), then Pi3 and MapAnything, with a streaming branch of Spann3R, CUT3R, and lingbot-map. This lab is built on '
        : 'Los modelos feed-forward de pointmap regresan geometría directo de los píxeles. El linaje corre DUSt3R (2023), luego MASt3R, luego VGGT (mejor paper CVPR 2025), luego Pi3 y MapAnything, con una rama streaming de Spann3R, CUT3R y lingbot-map. Este lab se construye sobre '}
        <b>lingbot-map</b> <Cite k="lingbot" />, {en ? 'the 2026 apex of the streaming branch (Apache-2.0).' : 'el ápice 2026 de la rama streaming (Apache-2.0).'}<Cite k="dust3r" /><Cite k="mast3r" /><Cite k="vggt" /><Cite k="pi3" /><Cite k="mapanything" /></p>
      <p>{en
        ? 'The shift matters because optimization-based SLAM is accurate but iterative and fragile to initialization, while a feed-forward pass is fast, robust, and streamable. The Methodology page traces the full lineage and the networks; the Benchmark page reports the numbers per model.'
        : 'El cambio importa porque el SLAM por optimización es preciso pero iterativo y frágil a la inicialización, mientras un forward feed-forward es rápido, robusto y streameable. La página de Metodología traza el linaje completo y las redes; la de Benchmark reporta los números por modelo.'}</p>
    </>
  );

  const lanes = (
    <>
      <h3>{en ? 'Three lanes (ADR-0057)' : 'Tres lanes (ADR-0057)'}</h3>
      <p>{en
        ? 'Because the model is a roughly 1B-parameter ViT that needs a GPU, it is not browser-feasible. The lab therefore separates three lanes: an offline lane that precomputes committed artifacts on a GPU, a replay lane (this static web) that renders those artifacts, and a dormant live lane (a local-GPU API) for real-time reconstruction of custom footage. The App page shown here is the replay lane, and it can play the reconstruction building up frame by frame.'
        : 'Como el modelo es un ViT de aproximadamente 1B parámetros que necesita GPU, no es viable en el browser. El lab separa tres lanes: uno offline que precalcula artefactos confirmados en GPU, uno replay (esta web estática) que los renderiza, y uno live dormido (una API GPU local) para reconstrucción en vivo de video propio. La App que se abre aquí es el lane replay, y puede reproducir la reconstrucción construyéndose cuadro a cuadro.'}</p>
      <p className="muted">{en ? 'Open the ⓘ Architecture button in the header for the full themed diagram of the three lanes and the data flow.' : 'Abrir el botón ⓘ Arquitectura en el header para el diagrama completo, adaptado al tema, de los tres lanes y el flujo de datos.'}</p>
    </>
  );

  return (
    <div className="page">
      <h2>{en ? 'Introduction' : 'Introducción'}</h2>
      <p className="lead">{en
        ? 'Lidar 3D is a research lab at the frontier of feed-forward 3D scene reconstruction: it turns a video stream into a camera trajectory, dense metric depth, and a live RGB point cloud, in real time, with no per-scene optimization.'
        : 'Lidar 3D es un lab en la frontera de la reconstrucción 3D feed-forward: convierte un stream de video en trayectoria de cámara, profundidad métrica densa y una nube de puntos RGB, en tiempo real, sin optimización por escena.'}</p>
      <SubTabs tabs={[
        { id: 'ov', label: en ? 'Overview' : 'Panorama', body: overview },
        { id: 'lin', label: en ? 'Lineage' : 'Linaje', body: <>{lineage}<Refs ids={['dust3r', 'mast3r', 'vggt', 'pi3', 'mapanything', 'spann3r', 'cut3r', 'lingbot']} /></> },
        { id: 'lanes', label: en ? 'Three lanes' : 'Tres lanes', body: lanes },
      ]} />
    </div>
  );
}
