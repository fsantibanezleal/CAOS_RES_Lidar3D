import { type Lang } from '../i18n';

export function Experiments({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <div className="page">
      <h2>{en ? 'Experiments' : 'Experimentos'}</h2>
      <p className="lead">{en
        ? 'Cases span categories: a synthetic CPU control (the CI smoke test) and four real sequences shipped with lingbot-map, baked offline on an 8 GB GPU. The App replays each; Experiments and Benchmark summarise across cases.'
        : 'Los casos cubren categorías: un control sintético CPU (el smoke de CI) y cuatro secuencias reales que vienen con lingbot-map, horneadas offline en una GPU de 8 GB. La App reproduce cada uno; Experimentos y Benchmark resumen entre casos.'}</p>

      <h3>{en ? 'Cases by category' : 'Casos por categoría'}</h3>
      <ul>
        <li><b>SYN_orbit</b> — {en ? 'synthetic procedural corridor (CPU, deterministic). A textured tunnel + forward camera; runs in &lt;1 s with no GPU/model, exercising the exact pipeline path so CI can smoke-test it.' : 'corredor procedural sintético (CPU, determinista). Un túnel texturizado + cámara hacia adelante; corre en &lt;1 s sin GPU/modelo, ejercitando el mismo camino del pipeline para que CI lo testee.'}</li>
        <li><b>oxford / university / loop / courthouse</b> — {en ? 'real sequences: an outdoor walk, a courtyard, a revisit (the loop-closure showcase), and a facade orbit.' : 'secuencias reales: una caminata exterior, un patio, un revisit (la vitrina de loop-closure) y una órbita de fachada.'}</li>
      </ul>

      <h3>{en ? 'The 8 GB-safe configuration (measured)' : 'La configuración segura para 8 GB (medida)'}</h3>
      <p>{en
        ? 'On an RTX 4070 Laptop (8 GB), lingbot-map runs with the SDPA attention backend (no FlashInfer build), CPU-offload, a reduced KV window (16), bf16, and a frame cap. Verified peak ~7.1 GB. The oxford bake produced a 193k-point RGB cloud over 48 frames with a 3.13 m trajectory.'
        : 'En una RTX 4070 Laptop (8 GB), lingbot-map corre con el backend SDPA (sin compilar FlashInfer), CPU-offload, una ventana KV reducida (16), bf16 y un tope de cuadros. Pico verificado ~7.1 GB. El bake de oxford produjo una nube RGB de 193k puntos sobre 48 cuadros con una trayectoria de 3.13 m.'}</p>

      <h3>{en ? 'Honesty' : 'Honestidad'}</h3>
      <p>{en
        ? 'The bundled example sequences carry no ground-truth poses, so the lab reports trajectory length, point count and confidence — and explicitly NOT ATE/RPE, which would be faked without ground truth. The synthetic case is clearly labelled synthetic. Per-case numbers are read from the committed manifests, never from a claim.'
        : 'Las secuencias de ejemplo no traen poses de referencia, así que el lab reporta longitud de trayectoria, cantidad de puntos y confianza — y explícitamente NO ATE/RPE, que serían inventados sin referencia. El caso sintético está etiquetado como sintético. Los números por caso se leen de los manifests commiteados, nunca de una afirmación.'}</p>
      <div><span className="tag">5 cases</span><span className="tag">synthetic control</span><span className="tag">measured, not claimed</span><span className="tag">no faked ATE</span></div>
    </div>
  );
}
