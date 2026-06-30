import { type Lang } from '../i18n';
import { Katex } from '../components/Katex';

export function Methodology({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <div className="page">
      <h2>{en ? 'Methodology' : 'Metodología'}</h2>
      <p className="lead">{en
        ? 'The engine is the Geometric Context Transformer (GCT): a DINOv2-backed ViT with 24 alternating frame / cross-frame attention blocks, driven causally with a compact three-tier context and a paged KV cache.'
        : 'El motor es el Geometric Context Transformer (GCT): un ViT con backbone DINOv2 y 24 bloques alternados de atención por-cuadro / entre-cuadros, ejecutado causalmente con un contexto compacto de tres niveles y un KV cache paginado.'}</p>

      <h3>{en ? 'Geometric Context Attention' : 'Geometric Context Attention'}</h3>
      <p>{en ? 'Each new frame attends to three contexts, each solving a distinct SLAM failure mode:' : 'Cada cuadro nuevo atiende a tres contextos, cada uno resolviendo un modo de falla de SLAM:'}</p>
      <ul>
        <li><b>{en ? 'Anchor context' : 'Contexto ancla'}:</b> {en ? 'the first n frames (full attention + a learnable token) fix the world coordinate frame and the metric scale, set from the anchor cloud as ' : 'los primeros n cuadros (atención completa + token aprendible) fijan el marco de coordenadas y la escala métrica, definida desde la nube ancla como '}<Katex tex={String.raw`s=\tfrac{1}{|\mathcal{X}|}\sum\|\mathbf{x}\|_2`} />.</li>
        <li><b>{en ? 'Pose-reference window' : 'Ventana de pose'}:</b> {en ? 'the k≈16–64 most recent frames at full token resolution give dense local geometry for accurate relative pose.' : 'los k≈16–64 cuadros recientes a resolución completa dan geometría local densa para pose relativa precisa.'}</li>
        <li><b>{en ? 'Trajectory memory' : 'Memoria de trayectoria'}:</b> {en ? 'all older frames are compressed to 6 tokens each (Video-RoPE ordered) for cheap long-range drift correction.' : 'los cuadros más viejos se comprimen a 6 tokens cada uno (orden Video-RoPE) para corregir drift de largo rango barato.'}</li>
      </ul>
      <p>{en ? 'The per-frame context is therefore ' : 'El contexto por cuadro es entonces '}<Katex tex={String.raw`(n+k)\,M + 6T`} />{en ? ' tokens (a constant part plus a tiny linear part), versus ' : ' tokens (una parte constante más una parte lineal diminuta), versus '}<Katex tex={String.raw`M\,T`} />{en ? ' for naive causal attention — about an 80× reduction over 10k frames, the key to streaming at ~20 FPS.' : ' para atención causal naive, una reducción de ~80× sobre 10k cuadros, la clave del streaming a ~20 FPS.'}</p>

      <h3>{en ? 'From depth to a colored cloud' : 'De profundidad a nube coloreada'}</h3>
      <p>{en ? 'The model emits a per-frame pose encoding and a dense depth map; the lab converts the pose to a camera-to-world matrix and unprojects depth with the (self-calibrated) intrinsics, colouring each point with its source pixel and filtering by the predicted confidence:' : 'El modelo emite una codificación de pose por cuadro y un mapa de profundidad denso; el lab convierte la pose a cámara-a-mundo y desproyecta la profundidad con los intrínsecos (auto-calibrados), coloreando cada punto con su píxel fuente y filtrando por la confianza predicha:'}</p>
      <Katex block tex={String.raw`\mathbf{X}^{(t)}_{world} = \mathbf{P}^{(t)}_{c2w}\begin{bmatrix}\frac{u-c_x}{f_x}D\\[2pt]\frac{v-c_y}{f_y}D\\[2pt]D\\[2pt]1\end{bmatrix},\quad \text{keep if } \sigma(u,v)\ge \tau_q`} />

      <h3>{en ? 'The novel agenda (what the lab adds)' : 'La agenda novel (lo que aporta el lab)'}</h3>
      <p>{en ? "The engine is used as-is; the lab's contribution is its three documented gaps, pursued rigorously: loop closure / pose-graph over the trajectory memory; camera↔LiDAR fusion (metric anchoring + drift correction); and an optional refinement (textured mesh / 3DGS) so a reconstruction reads as a surface, not a bare LiDAR map." : 'El motor se usa tal cual; el aporte del lab son sus tres gaps documentados, perseguidos con rigor: loop closure / pose-graph sobre la memoria de trayectoria; fusión cámara↔LiDAR (anclaje métrico + corrección de drift); y un refinado opcional (malla texturizada / 3DGS) para que una reconstrucción se vea como superficie, no como un mapa LiDAR pelado.'}</p>

      <p className="refs">lingbot-map: "Geometric Context Transformer for Streaming 3D Reconstruction", arXiv:2604.14141. Backbone: DINOv2 (arXiv:2304.07193), VGGT alternating attention (arXiv:2503.11651).</p>
    </div>
  );
}
