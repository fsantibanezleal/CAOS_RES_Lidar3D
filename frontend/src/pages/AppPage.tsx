// The App workbench: pick a case, REPLAY its committed reconstruction building up frame by frame, tune point
// density, toggle RGB vs LiDAR-depth color, pick a camera mode (orbit / first-person / top), and watch the
// per-frame depth image follow the player. Replay is opt-in-then-auto (single pass, pauses on a hidden tab).
import { useEffect, useMemo, useRef, useState } from 'react';
import { loadIndex, loadManifest, loadTrace } from '../api/artifacts';
import type { CaseIndex, CaseManifest, Trace } from '../lib/contract.types';
import { type Lang, t } from '../i18n';
import { CloudViewer, type CameraMode, type ColorMode } from '../render/CloudViewer';
import { DeckViewer } from '../render/DeckViewer';
import { PotreeViewer } from '../render/PotreeViewer';

const DETAIL_STRIDE = [8, 4, 3, 2, 1]; // point-density level 1(low)..5(full) -> draw-stride (start LOW for fluidity)
const es = (l: Lang) => l === 'es';
const defaultColor = (m: CaseManifest): ColorMode =>
  /lidar|icp|open3d/i.test(`${m.category} ${m.engine?.model ?? ''}`) ? 'depth' : 'rgb';

export function AppPage({ lang, dark }: { lang: Lang; dark: boolean }) {
  const [index, setIndex] = useState<CaseIndex | null>(null);
  const [sel, setSel] = useState('');
  const [manifest, setManifest] = useState<CaseManifest | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [err, setErr] = useState('');
  const [ptSize, setPtSize] = useState(0.016);
  const [detail, setDetail] = useState(1);
  const [reveal, setReveal] = useState(1);
  const [playing, setPlaying] = useState(false);
  const [colorMode, setColorMode] = useState<ColorMode>('rgb');
  const [camMode, setCamMode] = useState<CameraMode>('orbit');
  const [renderer, setRenderer] = useState<'three' | 'deck' | 'surfels' | 'potree'>('three');
  const [rightTab, setRightTab] = useState<'depth' | 'rgb'>('depth');
  const [showCones, setShowCones] = useState(true);
  const [showTraj, setShowTraj] = useState(true);
  const [showObb, setShowObb] = useState(false); // OBB + RGB axes overlay to compare the coordinate frame across renderers
  const raf = useRef(0);

  useEffect(() => {
    loadIndex().then((ix) => { setIndex(ix); setSel(ix.cases[0]?.case_id ?? ''); }).catch((e) => setErr(String(e)));
  }, []);
  useEffect(() => {
    if (!sel) return;
    setTrace(null); stopPlay(); setReveal(1);
    loadManifest(sel).then((m) => { setManifest(m); setColorMode(defaultColor(m)); return loadTrace(m.artifact.path); })
      .then(setTrace).catch((e) => setErr(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel]);
  useEffect(() => () => stopPlay(), []);
  useEffect(() => {
    if (!trace) return;
    const id = setTimeout(() => replay(), 120); // auto-play the build once (also guarantees the first paint)
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace]);

  function stopPlay() { if (raf.current) cancelAnimationFrame(raf.current); raf.current = 0; setPlaying(false); }
  function replay() {
    stopPlay(); setReveal(0); setPlaying(true);
    const dur = 7000, t0 = performance.now();
    const step = (now: number) => {
      const k = Math.min(1, (now - t0) / dur); setReveal(k);
      if (k < 1) raf.current = requestAnimationFrame(step); else { raf.current = 0; setPlaying(false); }
    };
    raf.current = requestAnimationFrame(step);
  }

  const byCat = useMemo(() => {
    const o: Record<string, string[]> = {};
    index?.cases.forEach((c) => (o[c.category] ??= []).push(c.case_id));
    return o;
  }, [index]);

  const thumbs = trace?.depth_thumbs ?? [];
  const rgbThumbs = trace?.rgb_thumbs ?? [];
  const shownPct = Math.round(reveal * 100);
  const curFrame = trace ? Math.round(reveal * Math.max(0, trace.n_frames - 1)) : 0;
  const near = (arr: { idx: number; png_b64: string }[]) =>
    arr.length ? arr.reduce((b, x) => (Math.abs(x.idx - curFrame) < Math.abs(b.idx - curFrame) ? x : b), arr[0]) : null;
  const depthT = near(thumbs); const rgbT = near(rgbThumbs);
  const CAMS: [CameraMode, string][] = [['orbit', es(lang) ? 'Órbita' : 'Orbit'], ['first', es(lang) ? '1ª persona' : 'First-person'], ['top', es(lang) ? 'Cenital' : 'Top']];

  return (
    <div className="work">
      <aside className="panel">
        <label className="lab">{t(lang, 'source')}</label>
        <select value={sel} onChange={(e) => setSel(e.target.value)}>
          {Object.entries(byCat).map(([cat, ids]) => (
            <optgroup key={cat} label={cat}>{ids.map((id) => <option key={id} value={id}>{id}</option>)}</optgroup>
          ))}
        </select>
        <p className="hint">{t(lang, 'replay_note')}</p>

        <label className="lab">{es(lang) ? 'Reproducción' : 'Replay'}</label>
        <div className="chips">
          <button className="chip on" onClick={playing ? stopPlay : replay}>
            {playing ? (es(lang) ? '⏸ Pausar' : '⏸ Pause') : (es(lang) ? '▶ Reproducir' : '▶ Replay')}
          </button>
          <span className="hint" style={{ alignSelf: 'center' }}>{shownPct}%</span>
        </div>
        <input type="range" min={0} max={1} step={0.01} value={reveal} onChange={(e) => { stopPlay(); setReveal(+e.target.value); }} />

        <label className="lab">{es(lang) ? 'Cámara' : 'Camera'}</label>
        <div className="chips">
          {CAMS.map(([m, lab]) => <button key={m} className={'chip' + (camMode === m ? ' on' : '')} onClick={() => setCamMode(m)}>{lab}</button>)}
        </div>

        <label className="lab">{es(lang) ? 'Superposiciones' : 'Overlays'}</label>
        <div className="chips">
          <button className={'chip' + (showCones ? ' on' : '')} onClick={() => setShowCones(!showCones)}>{es(lang) ? 'Conos' : 'Cones'}</button>
          <button className={'chip' + (showTraj ? ' on' : '')} onClick={() => setShowTraj(!showTraj)}>{es(lang) ? 'Trayectoria' : 'Trajectory'}</button>
          <button className={'chip' + (showObb ? ' on' : '')} onClick={() => setShowObb(!showObb)} title={es(lang) ? 'Caja + ejes RGB para comparar el sistema de coordenadas entre renderers' : 'Bounding box + RGB axes to compare the coordinate frame across renderers'}>{es(lang) ? 'Caja (OBB)' : 'Box (OBB)'}</button>
        </div>

        <label className="lab">{es(lang) ? 'Motor de render' : 'Renderer'}</label>
        <div className="chips">
          <button className={'chip' + (renderer === 'three' ? ' on' : '')} onClick={() => setRenderer('three')}>three.js</button>
          <button className={'chip' + (renderer === 'deck' ? ' on' : '')} onClick={() => setRenderer('deck')}>deck.gl</button>
          <button className={'chip' + (renderer === 'surfels' ? ' on' : '')} onClick={() => setRenderer('surfels')}>{es(lang) ? 'surfels' : 'surfels'}</button>
          <button className={'chip' + (renderer === 'potree' ? ' on' : '')} onClick={() => setRenderer('potree')}>Potree</button>
        </div>
        <p className="hint">{es(lang) ? 'three.js puntos · deck.gl GPU · surfels superficie · Potree LOD por octree (escala a millones)' : 'three.js points · deck.gl GPU · surfels surface · Potree octree LOD (scales to millions)'}</p>

        <label className="lab">{es(lang) ? 'Densidad de puntos' : 'Point density'}</label>
        <input type="range" min={1} max={5} step={1} value={detail} onChange={(e) => setDetail(+e.target.value)} />
        <p className="hint">{es(lang) ? 'Parte baja para fluidez; súbela hasta donde rinda tu equipo' : 'Starts low for fluidity; raise it as far as your machine handles'}</p>

        <label className="lab">Color</label>
        <div className="chips">
          <button className={'chip' + (colorMode === 'rgb' ? ' on' : '')} onClick={() => setColorMode('rgb')}>RGB</button>
          <button className={'chip' + (colorMode === 'depth' ? ' on' : '')} onClick={() => setColorMode('depth')}>{es(lang) ? 'Profundidad' : 'Depth'}</button>
        </div>

        <label className="lab">{t(lang, 'point_size')}</label>
        <input type="range" min={0.004} max={0.05} step={0.002} value={ptSize} onChange={(e) => setPtSize(+e.target.value)} />
        {err && <p style={{ color: 'var(--warn)' }}>error: {err}</p>}
      </aside>

      <section className="stage">
        {trace && (renderer === 'deck'
          ? <DeckViewer trace={trace} pointSize={ptSize} dark={dark} density={DETAIL_STRIDE[detail - 1]} reveal={reveal} colorMode={colorMode} cameraMode={camMode} showCones={showCones} showTraj={showTraj} showObb={showObb} />
          : renderer === 'potree'
            ? <PotreeViewer key={trace.case_id} trace={trace} pointSize={ptSize} dark={dark} density={DETAIL_STRIDE[detail - 1]} reveal={reveal} cameraMode={camMode} colorMode={colorMode} showObb={showObb} />
            : <CloudViewer trace={trace} pointSize={ptSize} dark={dark} density={DETAIL_STRIDE[detail - 1]} reveal={reveal} colorMode={colorMode} cameraMode={camMode} showCones={showCones} showTraj={showTraj} surfel={renderer === 'surfels'} showObb={showObb} />)}
        <div className="overlay">
          {trace ? `${trace.n_points.toLocaleString()} pts · ${trace.n_frames} frames · ${trace.path_length} m · ${shownPct}%` : 'loading…'}
        </div>
        {renderer === 'potree' && (
          <div className="overlay" style={{ top: 'auto', bottom: 8, right: 8, left: 'auto', maxWidth: 320, opacity: 0.85 }}>
            {es(lang)
              ? 'Potree renderiza por LOD (octree, escala a millones). El reveal descubre el mapa por clip espacial a lo largo del recorrido (potree-core no filtra por atributo por-punto); conos y trayectoria por cuadro son de three.js / deck.gl.'
              : 'Potree renders by LOD (octree, scales to millions). Reveal uncovers the map by spatial clipping along the path (potree-core has no per-point attribute filter); per-frame cones and trajectory live in three.js / deck.gl.'}
          </div>
        )}
      </section>

      <aside className="panel">
        <label className="lab">{es(lang) ? 'Vista por cuadro (sigue al player)' : 'Per-frame view (follows the player)'}</label>
        <div className="chips">
          <button className={'chip' + ((rightTab === 'depth' || !rgbT) ? ' on' : '')} onClick={() => setRightTab('depth')}>{es(lang) ? 'Profundidad' : 'Depth'}</button>
          {rgbT && <button className={'chip' + (rightTab === 'rgb' ? ' on' : '')} onClick={() => setRightTab('rgb')}>RGB</button>}
        </div>
        {(() => {
          const show = rightTab === 'rgb' && rgbT ? rgbT : depthT;
          return show
            ? <><img className="depth" src={show.png_b64} alt="per-frame view" /><p className="hint">{(rightTab === 'rgb' && rgbT) ? 'RGB' : (es(lang) ? 'Profundidad' : 'Depth')} · {es(lang) ? 'cuadro' : 'frame'} {show.idx}/{trace!.n_frames}</p></>
            : <p className="hint">{es(lang) ? 'sin vista para este caso' : 'no view for this case'}</p>;
        })()}
        {!rgbT && manifest && /lidar/i.test(manifest.category) && (
          <p className="hint">{es(lang)
            ? 'Caso LiDAR: el sensor es un láser, no hay stream RGB (el mapa se colorea por altura).'
            : 'LiDAR case: the sensor is a laser, there is no RGB stream (the map is height-colored).'}</p>
        )}

        {manifest && (
          <>
            <label className="lab">{t(lang, 'stats')}</label>
            <table className="stats"><tbody>
              <tr><td>{t(lang, 'engine')}</td><td>{manifest.engine.model}</td></tr>
              <tr><td>{t(lang, 'category')}</td><td>{manifest.category}</td></tr>
              <tr><td>{t(lang, 'points')}</td><td>{trace ? trace.n_points.toLocaleString() : '·'}</td></tr>
              <tr><td>{t(lang, 'frames')}</td><td>{manifest.params.max_frames}</td></tr>
              <tr><td>{t(lang, 'path')}</td><td>{trace ? `${trace.path_length} m` : '·'}</td></tr>
              <tr><td>{t(lang, 'lane')}</td><td>{manifest.lane}</td></tr>
              {manifest.dataset && <tr><td>{es(lang) ? 'Dataset' : 'Dataset'}</td><td>{manifest.dataset}</td></tr>}
              {manifest.license && <tr><td>{es(lang) ? 'Licencia' : 'License'}</td><td>{manifest.license}</td></tr>}
            </tbody></table>
          </>
        )}
      </aside>
    </div>
  );
}
