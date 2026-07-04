import { type Lang } from '../i18n';
import { SubTabs } from '../components/SubTabs';
import { Cite, Refs } from '../components/References';

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
        <tr><td><b>{en ? 'Estela (our depth+pose net)' : 'Estela (nuestra red profundidad+pose)'}</b> <Cite k="resnet" /></td><td><span className="tag novel">{en ? 'ours' : 'nuestro'}</span></td><td>{en ? 'trainable ResNet-18 depth + Siamese/correlation pose + ICP/TSDF refinement' : 'ResNet-18 entrenable de profundidad + pose Siamese/correlación + refinado ICP/TSDF'}</td><td>{en ? 'wired + LIVE (8 scenes, ~0.37 m held-out ATE)' : 'integrado + EN VIVO (8 escenas, ~0.37 m ATE held-out)'}</td></tr>
        <tr><td>{en ? 'Global pose-graph + loop closure (D1)' : 'Pose-graph global + loop closure (D1)'}</td><td><span className="tag novel">novel</span></td><td>{en ? 'Open3D multiway odometry + loop-closure edges, global optimization' : 'odometría multiway Open3D + aristas de loop-closure, optimización global'}</td><td>{en ? 'IMPLEMENTED (opt-in; pose-accuracy bound)' : 'IMPLEMENTADO (opt-in; acotado por precisión de pose)'}</td></tr>
        <tr><td>{en ? 'TSDF volumetric fusion' : 'Fusión volumétrica TSDF'}</td><td><span className="tag novel">{en ? 'ours' : 'nuestro'}</span></td><td>{en ? 'KinectFusion-style denoised surface from the depth+pose stream' : 'superficie denoised estilo KinectFusion desde el stream profundidad+pose'}</td><td>{en ? 'IMPLEMENTED (opt-in)' : 'IMPLEMENTADO (opt-in)'}</td></tr>
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

      <h3>{en ? 'Our own model: 8 scenes + a real held-out ATE' : 'Nuestro modelo: 8 escenas + un ATE held-out real'}</h3>
      <p className="hint">{en ? 'Estela has a REAL accuracy number, unlike the vendored engine on the un-GT-ed example clips: an Absolute Trajectory Error measured against ground truth on a truly held-out sequence.' : 'Estela tiene un número de precisión REAL, a diferencia del motor vendorizado sobre los clips sin GT: un Error Absoluto de Trayectoria medido contra referencia en una secuencia realmente held-out.'}<Cite k="tum" /><Cite k="umeyama" /></p>
      <table className="data"><thead>
        <tr><th>{en ? 'Metric' : 'Métrica'}</th><th className="num">{en ? 'Value' : 'Valor'}</th></tr>
      </thead><tbody>
        <tr><td>{en ? 'Held-out ATE (TUM long_office, ~300 frames, Umeyama-aligned)' : 'ATE held-out (TUM long_office, ~300 cuadros, alineado Umeyama)'}</td><td className="num"><b>~0.37 m</b></td></tr>
        <tr><td>{en ? 'Training data' : 'Datos de entrenamiento'}</td><td className="num">{en ? '11 TUM RGB-D seq + ICL-NUIM (~16k pairs)' : '11 seq TUM RGB-D + ICL-NUIM (~16k pares)'}</td></tr>
        <tr><td>{en ? 'Deployed scenes' : 'Escenas desplegadas'}</td><td className="num">{en ? '8 (4 truly held-out), 240 frames each' : '8 (4 realmente held-out), 240 cuadros c/u'}</td></tr>
        <tr><td>{en ? 'Fused cloud points (per scene)' : 'Puntos de nube fusionada (por escena)'}</td><td className="num">{en ? '~10k to 117k (ICP-refined + voxel)' : '~10k a 117k (ICP + vóxel)'}</td></tr>
      </tbody></table>
      <p className="muted">{en ? 'Honest: the ~0.37 m ATE is the pose accuracy that bounds a clean fused surface, which is why the global-pose-graph (D1) and TSDF refinements ship opt-in and the training set keeps growing. The per-frame depth is excellent; the fused map is pose-bound. See Model history (Experiments) for every training run.' : 'Honesto: el ATE ~0.37 m es la precisión de pose que acota una superficie fusionada limpia, por eso el pose-graph global (D1) y el refinado TSDF van opt-in y el set de entrenamiento sigue creciendo. La profundidad por-cuadro es excelente; el mapa fusionado está acotado por la pose. Ver Historial de modelos (Experimentos) para cada corrida.'}</p>
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
        { id: 'ladder', label: en ? 'Model ladder' : 'Escalera de modelos', body: <>{ladder}<Refs ids={['open3d', 'kissicp', 'lingbot', 'resnet']} /></> },
        { id: 'sota', label: en ? 'Camera SOTA' : 'SOTA cámara', body: <>{cameraSota}<Refs ids={['lingbot', 'cut3r', 'vggt', 'oxfordspires']} /></> },
        { id: 'measured', label: en ? 'Measured (this lab)' : 'Medido (este lab)', body: <>{measured}<Refs ids={['tum', 'umeyama', 'flashinfer']} /></> },
        { id: 'honesty', label: en ? 'Honesty' : 'Honestidad', body: honesty },
      ]} />
    </div>
  );
}
