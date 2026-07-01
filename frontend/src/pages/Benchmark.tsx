import { type Lang } from '../i18n';
import { SubTabs } from '../components/SubTabs';
import { Cite, References } from '../components/References';

export function Benchmark({ lang }: { lang: Lang }) {
  const en = lang === 'en';

  const ladder = (
    <>
      <h3>{en ? 'The models employed (the ladder)' : 'Los modelos empleados (la escalera)'}</h3>
      <p>{en
        ? 'This product runs a ladder of models: a classical baseline, the SOTA engine, and the novel proposals the lab evaluates beyond SOTA. Each row is a real, swappable component behind a common interface.'
        : 'Este producto corre una escalera de modelos: una línea base clásica, el motor SOTA y las propuestas novel que el lab evalúa más allá del SOTA. Cada fila es un componente real e intercambiable tras una interfaz común.'}</p>
      <table className="data"><thead>
        <tr><th>{en ? 'Model' : 'Modelo'}</th><th>{en ? 'Class' : 'Clase'}</th><th>{en ? 'Role' : 'Rol'}</th><th>{en ? 'Status' : 'Estado'}</th></tr>
      </thead><tbody>
        <tr><td>Open3D point-to-plane ICP <Cite k="open3d" /></td><td><span className="tag classical">{en ? 'classical' : 'clásico'}</span></td><td>{en ? 'LiDAR frame-to-frame odometry baseline' : 'odometría LiDAR cuadro-a-cuadro (base)'}</td><td>{en ? 'wired (LiDAR cases)' : 'integrado (casos LiDAR)'}</td></tr>
        <tr><td>KISS-ICP <Cite k="kissicp" /></td><td><span className="tag classical">{en ? 'classical' : 'clásico'}</span></td><td>{en ? 'SOTA LiDAR-only odometry' : 'odometría LiDAR-only SOTA'}</td><td>{en ? 'pinned, swappable' : 'fijado, intercambiable'}</td></tr>
        <tr><td>lingbot-map GCT <Cite k="lingbot" /></td><td><span className="tag sota">SOTA</span></td><td>{en ? 'camera streaming reconstruction' : 'reconstrucción de cámara en streaming'}</td><td>{en ? 'wired (camera cases)' : 'integrado (casos cámara)'}</td></tr>
        <tr><td>{en ? 'Loop-closure head (D1)' : 'Cabeza loop-closure (D1)'}</td><td><span className="tag novel">novel</span></td><td>{en ? 'retrieval + pose-graph on the frozen GCT memory' : 'retrieval + pose-graph sobre la memoria GCT congelada'}</td><td>{en ? 'proposed (Experiments)' : 'propuesto (Experimentos)'}</td></tr>
        <tr><td>{en ? 'Camera + LiDAR fusion (D2)' : 'Fusión cámara + LiDAR (D2)'}</td><td><span className="tag novel">novel</span></td><td>{en ? 'metric anchoring + drift correction' : 'anclaje métrico + corrección de drift'}</td><td>{en ? 'proposed' : 'propuesto'}</td></tr>
        <tr><td>{en ? 'Constant-memory recurrence (D3)' : 'Recurrencia de memoria constante (D3)'}</td><td><span className="tag novel">novel</span></td><td>{en ? 'test-time training / LaCT O(1) state' : 'test-time training / estado LaCT O(1)'}</td><td>{en ? 'proposed' : 'propuesto'}</td></tr>
      </tbody></table>
      <p className="muted">{en ? 'Classical baselines make the SOTA gains legible; the novel rows are hypotheses evaluated on the Experiments page, with null results kept.' : 'Las líneas base clásicas hacen legibles las ganancias del SOTA; las filas novel son hipótesis evaluadas en Experimentos, conservando resultados nulos.'}</p>
    </>
  );

  const cameraSota = (
    <>
      <h3>{en ? 'Camera models: reported ATE (lingbot-map paper)' : 'Modelos de cámara: ATE reportado (paper lingbot-map)'}</h3>
      <p className="hint">{en ? 'Absolute Trajectory Error in metres, lower is better. Paper numbers for online/streaming methods (arXiv:2604.14141), not our reproduction.' : 'Error Absoluto de Trayectoria en metros, menor es mejor. Números del paper para métodos online/streaming (arXiv:2604.14141), no nuestra reproducción.'}<Cite k="lingbot" /></p>
      <table className="data"><thead>
        <tr><th>{en ? 'Model' : 'Modelo'}</th><th className="num">Oxford-Spires {en ? 'sparse' : 'sparse'} ATE↓</th><th className="num">Oxford-Spires {en ? 'dense 3.8k' : 'denso 3.8k'} ATE↓</th></tr>
      </thead><tbody>
        <tr><td><b>lingbot-map</b> <span className="tag sota">SOTA</span></td><td className="num"><b>6.42</b></td><td className="num"><b>7.11</b></td></tr>
        <tr><td>CUT3R <Cite k="cut3r" /></td><td className="num">18.16</td><td className="num">32.47</td></tr>
        <tr><td>VGGT <Cite k="vggt" /></td><td className="num">24.78</td><td className="num">{en ? 'n/a' : 'n/d'}</td></tr>
      </tbody></table>
      <p>{en ? 'The dense column is the honest target this lab works against: lingbot degrades only slightly from sparse to dense (6.42 to 7.11) while CUT3R nearly doubles (18.16 to 32.47). The novel loop-closure head (D1) is judged by whether it reduces the 7.11 m dense ATE from a frozen-backbone add-on.' : 'La columna densa es el objetivo honesto contra el que trabaja este lab: lingbot se degrada apenas de sparse a denso (6.42 a 7.11) mientras CUT3R casi se duplica (18.16 a 32.47). La cabeza novel de loop-closure (D1) se juzga por si reduce el ATE denso de 7.11 m desde un add-on de backbone congelado.'}<Cite k="oxfordspires" /></p>

      <h3>{en ? 'Engine capability (reported)' : 'Capacidad del motor (reportada)'}</h3>
      <table className="data"><thead>
        <tr><th>{en ? 'Benchmark' : 'Benchmark'}</th><th className="num">lingbot-map</th><th className="num">{en ? 'next best' : 'siguiente mejor'}</th></tr>
      </thead><tbody>
        <tr><td>ETH3D {en ? 'reconstruction F1↑' : 'reconstrucción F1↑'}</td><td className="num">98.98</td><td className="num">77.28</td></tr>
        <tr><td>7-Scenes ATE↓</td><td className="num">0.08</td><td className="num">{en ? '(see paper)' : '(ver paper)'}</td></tr>
        <tr><td>Tanks &amp; Temples AUC@30↑</td><td className="num">92.80</td><td className="num">{en ? '(see paper)' : '(ver paper)'}</td></tr>
        <tr><td>{en ? 'Throughput @518×378' : 'Throughput @518×378'}</td><td className="num" colSpan={2}>{en ? '~20 FPS over 10k+ frames (datacenter GPU)' : '~20 FPS sobre 10k+ cuadros (GPU datacenter)'}</td></tr>
      </tbody></table>
    </>
  );

  const measured = (
    <>
      <h3>{en ? 'This lab: measured on our hardware' : 'Este lab: medido en nuestro hardware'}</h3>
      <p className="hint">{en ? 'From the committed manifests (RTX 4070 Laptop, 8 GB-safe config: SDPA, CPU offload, sliding KV window). We report what we can measure without ground truth.' : 'De los manifests commiteados (RTX 4070 Laptop, config segura 8 GB: SDPA, offload a CPU, ventana KV deslizante). Reportamos lo que podemos medir sin referencia.'}</p>
      <table className="data"><thead>
        <tr><th>{en ? 'Case' : 'Caso'}</th><th>{en ? 'Engine' : 'Motor'}</th><th className="num">{en ? 'Points' : 'Puntos'}</th><th className="num">{en ? 'Frames' : 'Cuadros'}</th><th className="num">{en ? 'Path' : 'Trayecto'}</th></tr>
      </thead><tbody>
        <tr><td>oxford <span className="tag">{en ? 'real, GPU' : 'real, GPU'}</span></td><td>lingbot-map GCT</td><td className="num">193k</td><td className="num">48</td><td className="num">3.13 m</td></tr>
        <tr><td>SYN_orbit <span className="tag">{en ? 'synthetic, CPU' : 'sintético, CPU'}</span></td><td>{en ? 'synthetic camera' : 'cámara sintética'}</td><td className="num">108k</td><td className="num">40</td><td className="num">5.52 m</td></tr>
        <tr><td>LID_synthetic <span className="tag">{en ? 'synthetic, CPU' : 'sintético, CPU'}</span></td><td>Open3D ICP</td><td className="num">72k</td><td className="num">30</td><td className="num">5.01 m</td></tr>
      </tbody></table>
      <p className="muted">{en ? 'Peak VRAM ~7.1 GB on the real camera case; artifact size ~2 to 3 MB per case (decimated, base64). These are engineering measurements, not accuracy claims.' : 'VRAM pico ~7.1 GB en el caso real de cámara; tamaño de artefacto ~2 a 3 MB por caso (decimado, base64). Son mediciones de ingeniería, no afirmaciones de precisión.'}</p>
    </>
  );

  const honesty = (
    <>
      <h3>{en ? 'Honesty' : 'Honestidad'}</h3>
      <p>{en
        ? 'We do not claim to reproduce the paper ATE/RPE: the bundled sequences carry no ground truth, and full-dataset reproduction (Oxford-Spires, ETH3D) is offline work not yet done here. The engine numbers are cited; our numbers are measured. The lab own contribution (loop closure, LiDAR fusion, refinement) is evaluated as it lands, and null results are kept in the record.'
        : 'No afirmamos reproducir el ATE/RPE del paper: las secuencias no traen referencia, y la reproducción de datasets completos (Oxford-Spires, ETH3D) es trabajo offline aún no hecho aquí. Los números del motor están citados; los nuestros, medidos. El aporte propio del lab (loop closure, fusión LiDAR, refinado) se evalúa a medida que llega, y los resultados nulos se conservan en el registro.'}</p>
      <ul>
        <li><b>{en ? 'Cited' : 'Citado'}:</b> {en ? 'every reported SOTA number is from the lingbot-map paper and its cited baselines.' : 'cada número SOTA reportado es del paper de lingbot-map y sus baselines citadas.'}</li>
        <li><b>{en ? 'Measured' : 'Medido'}:</b> {en ? 'points, frames, path length, VRAM and artifact size come from our own committed manifests.' : 'puntos, cuadros, longitud de trayecto, VRAM y tamaño de artefacto vienen de nuestros manifests commiteados.'}</li>
        <li><b>{en ? 'Planned' : 'Planeado'}:</b> {en ? 'ground-truth ATE/RPE on Oxford-Spires and the novel D1 experiment are the next offline runs.' : 'ATE/RPE con referencia en Oxford-Spires y el experimento novel D1 son las próximas corridas offline.'}</li>
      </ul>
    </>
  );

  return (
    <div className="page">
      <h2>Benchmark</h2>
      <p className="lead">{en
        ? 'Results for the different models employed: the classical baselines, the SOTA engine reported numbers, and this lab measured numbers, kept separate and honestly labelled.'
        : 'Resultados para los distintos modelos empleados: las líneas base clásicas, los números reportados del motor SOTA y los números medidos por este lab, separados y etiquetados honestamente.'}</p>
      <SubTabs tabs={[
        { id: 'ladder', label: en ? 'Model ladder' : 'Escalera de modelos', body: ladder },
        { id: 'sota', label: en ? 'Camera SOTA' : 'SOTA cámara', body: cameraSota },
        { id: 'measured', label: en ? 'Measured (this lab)' : 'Medido (este lab)', body: measured },
        { id: 'honesty', label: en ? 'Honesty' : 'Honestidad', body: honesty },
      ]} />
      <h3>{en ? 'References' : 'Referencias'}</h3>
      <References only={['lingbot', 'cut3r', 'vggt', 'oxfordspires', 'kissicp', 'open3d', 'kitti']} />
    </div>
  );
}
