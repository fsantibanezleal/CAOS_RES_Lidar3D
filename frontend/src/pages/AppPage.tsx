// The App workbench: pick a case, REPLAY its committed reconstruction building up frame by frame (the "watch the
// data flow" idea), tune point density for a fluid response, toggle RGB (camera texture) vs LiDAR-depth color, and
// inspect the per-frame depth image + reconstruction stats. Reacts to the case selector (ADR-0016 App = a real
// workbench). Replay is opt-in (default static), runs once, stops, and pauses on a hidden tab (no compute bomb).
import { useEffect, useMemo, useRef, useState } from 'react';
import { loadIndex, loadManifest, loadTrace } from '../api/artifacts';
import type { CaseIndex, CaseManifest, Trace } from '../lib/contract.types';
import { type Lang, t } from '../i18n';
import { CloudViewer, type ColorMode } from '../render/CloudViewer';

const DETAIL_STRIDE = [8, 4, 3, 2, 1]; // point-density level 1(low)..5(full) -> draw-stride (start LOW for fluidity)
const es = (l: Lang) => l === 'es';
// a LiDAR case has no camera texture -> default to the height ramp; a camera case -> real RGB (ADR: RGB only if it exists)
const defaultColor = (m: CaseManifest): ColorMode =>
  /lidar|icp|open3d/i.test(`${m.category} ${m.engine?.model ?? ''}`) ? 'depth' : 'rgb';

export function AppPage({ lang, dark }: { lang: Lang; dark: boolean }) {
  const [index, setIndex] = useState<CaseIndex | null>(null);
  const [sel, setSel] = useState('');
  const [manifest, setManifest] = useState<CaseManifest | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [err, setErr] = useState('');
  const [ptSize, setPtSize] = useState(0.016);
  const [thumb, setThumb] = useState(0);
  const [detail, setDetail] = useState(1);            // density: starts LOW; not persisted -> resets to low on refresh
  const [reveal, setReveal] = useState(1);            // 1 = full cloud shown (replay animates 0 -> 1)
  const [playing, setPlaying] = useState(false);
  const [colorMode, setColorMode] = useState<ColorMode>('rgb');
  const raf = useRef(0);

  useEffect(() => {
    loadIndex().then((ix) => { setIndex(ix); setSel(ix.cases[0]?.case_id ?? ''); }).catch((e) => setErr(String(e)));
  }, []);
  useEffect(() => {
    if (!sel) return;
    setTrace(null); setThumb(0); stopPlay(); setReveal(1);
    loadManifest(sel).then((m) => { setManifest(m); setColorMode(defaultColor(m)); return loadTrace(m.artifact.path); })
      .then(setTrace).catch((e) => setErr(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sel]);
  useEffect(() => () => stopPlay(), []); // cancel any rAF on unmount
  // On case load, auto-play the reconstruction building up once (Felipe's "watch the data flow generate" idea).
  // It runs a single pass then stops (no loop, pauses on a hidden tab) and also guarantees the first WebGL paint,
  // which a static initial frame can otherwise composite blank.
  useEffect(() => {
    if (!trace) return;
    const id = setTimeout(() => replay(), 120);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace]);

  function stopPlay() { if (raf.current) cancelAnimationFrame(raf.current); raf.current = 0; setPlaying(false); }
  function replay() {
    stopPlay(); setReveal(0); setPlaying(true);
    const dur = 7000, t0 = performance.now();
    const step = (now: number) => { // rAF is paused by the browser on a hidden tab -> the replay pauses too
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
  const ti = Math.min(thumb, Math.max(0, thumbs.length - 1));
  const shownPct = Math.round(reveal * 100);

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
        <input type="range" min={0} max={1} step={0.01} value={reveal}
          onChange={(e) => { stopPlay(); setReveal(+e.target.value); }} />
        <p className="hint">{es(lang) ? 'Ver cómo se reconstruye cuadro a cuadro' : 'Watch the reconstruction build frame by frame'}</p>

        <label className="lab">{es(lang) ? 'Densidad de puntos' : 'Point density'}</label>
        <input type="range" min={1} max={5} step={1} value={detail} onChange={(e) => setDetail(+e.target.value)} />
        <p className="hint">{es(lang) ? 'Parte baja para fluidez; súbela hasta donde rinda tu equipo' : 'Starts low for fluidity; raise it as far as your machine handles'}</p>

        <label className="lab">Color</label>
        <div className="chips">
          <button className={'chip' + (colorMode === 'rgb' ? ' on' : '')} onClick={() => setColorMode('rgb')}>RGB</button>
          <button className={'chip' + (colorMode === 'depth' ? ' on' : '')} onClick={() => setColorMode('depth')}>{es(lang) ? 'Profundidad' : 'Depth'}</button>
        </div>
        <p className="hint">{es(lang) ? 'RGB si hay cámara; profundidad = mapa de altura LiDAR' : 'RGB when camera texture exists; depth = LiDAR height map'}</p>

        <label className="lab">{t(lang, 'point_size')}</label>
        <input type="range" min={0.004} max={0.04} step={0.002} value={ptSize} onChange={(e) => setPtSize(+e.target.value)} />

        {err && <p style={{ color: 'var(--warn)' }}>error: {err}</p>}
        {manifest && (
          <>
            <label className="lab">{t(lang, 'stats')}</label>
            <table className="stats"><tbody>
              <tr><td>{t(lang, 'engine')}</td><td>{manifest.engine.model}</td></tr>
              <tr><td>{t(lang, 'category')}</td><td>{manifest.category}</td></tr>
              <tr><td>{t(lang, 'frames')}</td><td>{manifest.params.max_frames}</td></tr>
              <tr><td>{t(lang, 'points')}</td><td>{trace ? trace.n_points.toLocaleString() : '—'}</td></tr>
              <tr><td>{t(lang, 'path')}</td><td>{trace ? `${trace.path_length} m` : '—'}</td></tr>
              <tr><td>{t(lang, 'lane')}</td><td>{manifest.lane}</td></tr>
              <tr><td>{t(lang, 'refine')}</td><td>{manifest.refine?.refined ? 'cleaned (open3d)' : 'colored cloud'}</td></tr>
            </tbody></table>
            <p className="hint">{t(lang, 'expected')}: {manifest.expected_band}</p>
          </>
        )}
      </aside>

      <section className="stage">
        {trace && <CloudViewer trace={trace} pointSize={ptSize} dark={dark} density={DETAIL_STRIDE[detail - 1]} reveal={reveal} colorMode={colorMode} />}
        <div className="overlay">
          {trace ? `${trace.n_points.toLocaleString()} pts · ${trace.n_frames} frames · ${trace.path_length} m · ${shownPct}%` : 'loading…'}
        </div>
      </section>

      <aside className="panel">
        <label className="lab">{es(lang) ? 'Profundidad por cuadro' : 'Per-frame depth'}</label>
        {thumbs.length > 0 ? (
          <>
            <img className="depth" src={thumbs[ti].png_b64} alt="depth" />
            <input type="range" min={0} max={thumbs.length - 1} step={1} value={ti} onChange={(e) => setThumb(+e.target.value)} />
            <p className="hint">frame {thumbs[ti].idx}</p>
          </>
        ) : <p className="hint">—</p>}
      </aside>
    </div>
  );
}
