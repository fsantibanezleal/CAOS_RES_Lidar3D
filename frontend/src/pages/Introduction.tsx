import { type Lang } from '../i18n';
import { Katex } from '../components/Katex';

export function Introduction({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <div className="page">
      <h2>{en ? 'Introduction' : 'Introducción'}</h2>
      <p className="lead">{en
        ? 'Lidar 3D is a research lab at the frontier of feed-forward 3D scene reconstruction: it turns a video stream into a camera trajectory, dense metric depth, and a live RGB point cloud, in real time, with no per-scene optimization.'
        : 'Lidar 3D es un lab en la frontera de la reconstrucción 3D feed-forward: convierte un stream de video en trayectoria de cámara, profundidad métrica densa y una nube de puntos RGB, en tiempo real, sin optimización por escena.'}</p>

      <h3>{en ? 'The problem' : 'El problema'}</h3>
      <p>{en
        ? 'Streaming 3D reconstruction recovers, at each incoming frame t and using only the current and past frames, the absolute camera pose, a dense depth map, and (by reprojection) a point cloud, with geometric accuracy, temporal consistency and bounded compute. Classically this is SLAM (tracking + mapping + bundle adjustment). The frontier replaces that optimization with a single transformer forward pass.'
        : 'La reconstrucción 3D en streaming recupera, en cada cuadro t y usando solo el cuadro actual y los pasados, la pose absoluta de cámara, un mapa de profundidad denso y (por reproyección) una nube de puntos, con precisión geométrica, consistencia temporal y cómputo acotado. Clásicamente esto es SLAM; la frontera reemplaza esa optimización por un solo forward de un transformer.'}</p>

      <h3>{en ? 'The state of the art (the lineage)' : 'El estado del arte (el linaje)'}</h3>
      <p>{en
        ? 'Feed-forward "pointmap" models regress geometry directly from pixels: DUSt3R (2023) → MASt3R → VGGT (CVPR 2025 best paper) → π³ → MapAnything, with a streaming branch (Spann3R → CUT3R → StreamVGGT → lingbot-map). This lab is built on '
        : 'Los modelos feed-forward de "pointmap" regresan geometría directo de los píxeles: DUSt3R (2023) → MASt3R → VGGT (mejor paper CVPR 2025) → π³ → MapAnything, con una rama streaming (Spann3R → CUT3R → StreamVGGT → lingbot-map). Este lab se construye sobre '}
        <b>lingbot-map</b> (arXiv:2604.14141), {en ? 'the 2026 apex of the streaming branch (Apache-2.0).' : 'el ápice 2026 de la rama streaming (Apache-2.0).'}</p>
      <p>{en ? 'A pointmap is a per-pixel 3D position in a common frame; given a depth map D and intrinsics K, a pixel (u,v) unprojects to a camera-frame point and then to the world via the camera-to-world pose:' : 'Un pointmap es una posición 3D por píxel en un marco común; dada una profundidad D e intrínsecos K, un píxel (u,v) se desproyecta a un punto en el marco de cámara y luego al mundo vía la pose cámara-a-mundo:'}</p>
      <Katex block tex={String.raw`\mathbf{X}_{world} = \mathbf{R}_{c2w}\,\underbrace{D(u,v)\,\mathbf{K}^{-1}[u,v,1]^\top}_{\text{camera-frame point}} + \mathbf{t}_{c2w}`} />

      <h3>{en ? 'Three lanes (ADR-0057)' : 'Tres lanes (ADR-0057)'}</h3>
      <p>{en
        ? 'Because the model is a ~1B-parameter ViT needing a GPU, it is not browser-feasible. The lab therefore separates: an OFFLINE lane that bakes committed artifacts on a GPU, a REPLAY lane (this static web) that renders those artifacts, and a dormant LIVE lane (a local-GPU API) for real-time reconstruction of your own footage. The App page you can open here is the replay lane.'
        : 'Como el modelo es un ViT de ~1B parámetros que necesita GPU, no es viable en el browser. El lab separa: un lane OFFLINE que hornea artefactos commiteados en GPU, un lane REPLAY (esta web estática) que los renderiza, y un lane LIVE dormido (una API GPU local) para reconstrucción en vivo de tu propio video. La App que abres aquí es el lane replay.'}</p>

      <p className="refs">References: lingbot-map (arXiv:2604.14141) · VGGT (arXiv:2503.11651) · DUSt3R (arXiv:2312.14132) · π³ (arXiv:2507.13347). Full survey in the repo docs/research.</p>
      <div>
        <span className="tag">feed-forward</span><span className="tag">streaming SLAM</span>
        <span className="tag">pointmap</span><span className="tag">Apache-2.0 engine</span>
      </div>
    </div>
  );
}
