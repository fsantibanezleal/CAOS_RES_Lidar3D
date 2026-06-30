import { type Lang } from '../i18n';

export function Benchmark({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <div className="page">
      <h2>Benchmark</h2>
      <p className="lead">{en
        ? "The engine's published SOTA (from the lingbot-map paper) and this lab's own measured numbers, kept separate and honestly labelled."
        : 'El SOTA publicado del motor (del paper de lingbot-map) y los números medidos por este lab, separados y etiquetados honestamente.'}</p>

      <h3>{en ? 'Engine SOTA — reported by the lingbot-map paper (arXiv:2604.14141)' : 'SOTA del motor — reportado por el paper de lingbot-map (arXiv:2604.14141)'}</h3>
      <p className="hint">{en ? 'These are the paper\'s numbers (online/streaming methods), not our reproduction. Lower ATE is better; higher F1 is better.' : 'Estos son números del paper (métodos online/streaming), no nuestra reproducción. Menor ATE es mejor; mayor F1 es mejor.'}</p>
      <table className="stats"><tbody>
        <tr><td>Oxford-Spires ATE (sparse)</td><td>lingbot 6.42 · CUT3R 18.16 · VGGT 24.78</td></tr>
        <tr><td>Oxford-Spires ATE (dense 3.8k)</td><td>lingbot 7.11 (Δ+0.69) · CUT3R 32.47</td></tr>
        <tr><td>ETH3D reconstruction F1</td><td>lingbot 98.98 · next best 77.28</td></tr>
        <tr><td>7-Scenes ATE</td><td>lingbot 0.08</td></tr>
        <tr><td>Tanks &amp; Temples AUC@30</td><td>lingbot 92.80</td></tr>
        <tr><td>Throughput @518×378</td><td>~20 FPS over 10k+ frames (datacenter GPU)</td></tr>
      </tbody></table>

      <h3>{en ? 'This lab — measured on our hardware' : 'Este lab — medido en nuestro hardware'}</h3>
      <p className="hint">{en ? 'From the committed manifests (RTX 4070 Laptop, 8 GB-safe config). We report what we can measure without ground truth.' : 'De los manifests commiteados (RTX 4070 Laptop, config segura 8 GB). Reportamos lo que podemos medir sin referencia.'}</p>
      <table className="stats"><tbody>
        <tr><td>oxford (real, GPU)</td><td>193k pts · 48 frames · 3.13 m · ~7.1 GB peak</td></tr>
        <tr><td>SYN_orbit (synthetic, CPU)</td><td>122k pts · 40 frames · 5.52 m · &lt;1 s</td></tr>
        <tr><td>artifact size</td><td>~2–3 MB per case (decimated, base64)</td></tr>
      </tbody></table>

      <h3>{en ? 'Honesty' : 'Honestidad'}</h3>
      <p>{en
        ? 'We do not claim to reproduce the paper\'s ATE/RPE: the bundled sequences have no ground truth, and full-dataset reproduction (Oxford-Spires, ETH3D) is offline work that is not yet done here. The engine numbers are cited; our numbers are measured. The lab\'s own contribution (loop closure, LiDAR fusion, refinement) is evaluated as it lands, with null results kept.'
        : 'No afirmamos reproducir el ATE/RPE del paper: las secuencias no traen referencia, y la reproducción de datasets completos (Oxford-Spires, ETH3D) es trabajo offline aún no hecho aquí. Los números del motor están citados; los nuestros, medidos. El aporte propio del lab (loop closure, fusión LiDAR, refinado) se evalúa a medida que llega, conservando resultados nulos.'}</p>
    </div>
  );
}
