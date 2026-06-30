// The replay SPA: list cases grouped by CATEGORY, select one, replay its committed trace (CONTRACT 2). The
// always-available static path (ADR-0054); the optional Pyodide live lane (src/pyodide) is the recompute upgrade.
import { useEffect, useMemo, useState } from 'react';
import { loadIndex, loadManifest, loadTrace } from './api/artifacts';
import type { CaseIndex, CaseManifest, Trace } from './lib/contract.types';
import { SIRChart } from './render/SIRChart';

export default function App() {
  const [index, setIndex] = useState<CaseIndex | null>(null);
  const [sel, setSel] = useState('');
  const [manifest, setManifest] = useState<CaseManifest | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    loadIndex()
      .then((ix) => {
        setIndex(ix);
        setSel(ix.cases[0]?.case_id ?? '');
      })
      .catch((e: unknown) => setErr(String(e)));
  }, []);

  useEffect(() => {
    if (!sel) return;
    loadManifest(sel)
      .then((m) => {
        setManifest(m);
        return loadTrace(m.artifact.path);
      })
      .then(setTrace)
      .catch((e: unknown) => setErr(String(e)));
  }, [sel]);

  const byCategory = useMemo(() => {
    const out: Record<string, string[]> = {};
    index?.cases.forEach((c) => (out[c.category] ??= []).push(c.case_id));
    return out;
  }, [index]);

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 900, margin: '2rem auto', padding: '0 1rem' }}>
      <h1>Product — deterministic replay</h1>
      <p>Replaying committed artifacts (CONTRACT 2). {index?.n_cases ?? 0} cases across {Object.keys(byCategory).length} categories.</p>
      {err && <p style={{ color: '#f85149' }}>error: {err}</p>}
      <label>
        Case:{' '}
        <select value={sel} onChange={(e) => setSel(e.target.value)}>
          {Object.entries(byCategory).map(([cat, ids]) => (
            <optgroup key={cat} label={cat}>
              {ids.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      {manifest && (
        <p>
          lane: <b>{manifest.lane}</b> — <i>{manifest.expected_band}</i>
        </p>
      )}
      {trace && <SIRChart trace={trace} />}
      {trace && (
        <p>
          peak I: {trace.summary.peak_I} at t={trace.summary.t_peak} · attack rate {trace.summary.attack_rate}
        </p>
      )}
    </main>
  );
}
