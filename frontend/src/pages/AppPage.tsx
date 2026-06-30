// The App workbench: pick a case, replay its committed RGB-colored reconstruction in 3D, inspect per-frame
// depth + reconstruction stats. Reacts to the case selector (ADR-0016 App = a real workbench).
import { useEffect, useMemo, useState } from 'react';
import { loadIndex, loadManifest, loadTrace } from '../api/artifacts';
import type { CaseIndex, CaseManifest, Trace } from '../lib/contract.types';
import { type Lang, t } from '../i18n';
import { CloudViewer } from '../render/CloudViewer';

export function AppPage({ lang, dark }: { lang: Lang; dark: boolean }) {
  const [index, setIndex] = useState<CaseIndex | null>(null);
  const [sel, setSel] = useState('');
  const [manifest, setManifest] = useState<CaseManifest | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [err, setErr] = useState('');
  const [ptSize, setPtSize] = useState(0.012);
  const [thumb, setThumb] = useState(0);

  useEffect(() => {
    loadIndex().then((ix) => { setIndex(ix); setSel(ix.cases[0]?.case_id ?? ''); }).catch((e) => setErr(String(e)));
  }, []);
  useEffect(() => {
    if (!sel) return;
    setTrace(null); setThumb(0);
    loadManifest(sel).then((m) => { setManifest(m); return loadTrace(m.artifact.path); })
      .then(setTrace).catch((e) => setErr(String(e)));
  }, [sel]);

  const byCat = useMemo(() => {
    const o: Record<string, string[]> = {};
    index?.cases.forEach((c) => (o[c.category] ??= []).push(c.case_id));
    return o;
  }, [index]);

  const thumbs = trace?.depth_thumbs ?? [];
  const ti = Math.min(thumb, Math.max(0, thumbs.length - 1));

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
              <tr><td>{t(lang, 'refine')}</td><td>{manifest.refine?.refined ? 'mesh+cloud' : 'colored cloud'}</td></tr>
            </tbody></table>
            <p className="hint">{t(lang, 'expected')}: {manifest.expected_band}</p>
          </>
        )}
      </aside>

      <section className="stage">
        {trace && <CloudViewer trace={trace} pointSize={ptSize} dark={dark} />}
        <div className="overlay">
          {trace ? `${trace.n_points.toLocaleString()} pts · ${trace.n_frames} frames · ${trace.path_length} m` : 'loading…'}
        </div>
      </section>

      <aside className="panel">
        <label className="lab">{t(lang, 'live_depth')}</label>
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
