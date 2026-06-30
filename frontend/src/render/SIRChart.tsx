// A minimal dependency-free SVG line chart of an SIR trace (S/I/R over time). EXAMPLE renderer — a real product
// uses its domain-appropriate, interactive visualizations here.
import type { Trace } from '../lib/contract.types';

const SERIES: ReadonlyArray<readonly [keyof Pick<Trace, 'S' | 'I' | 'R'>, string]> = [
  ['S', '#58a6ff'],
  ['I', '#f85149'],
  ['R', '#3fb950'],
];

export function SIRChart({ trace }: { trace: Trace }) {
  const W = 640;
  const H = 320;
  const pad = 36;
  const n = trace.t.length;
  const yMax = Math.max(1, ...trace.S, ...trace.I, ...trace.R);
  const tMax = trace.t[n - 1] || 1;
  const x = (i: number) => pad + (trace.t[i] / tMax) * (W - 2 * pad);
  const y = (v: number) => H - pad - (v / yMax) * (H - 2 * pad);
  const path = (arr: number[]) => arr.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="SIR trajectory" style={{ maxWidth: 680 }}>
      <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} stroke="#888" />
      <line x1={pad} y1={pad} x2={pad} y2={H - pad} stroke="#888" />
      {SERIES.map(([k, c]) => (
        <path key={k} d={path(trace[k])} fill="none" stroke={c} strokeWidth={2} />
      ))}
      {SERIES.map(([k, c], i) => (
        <text key={k} x={W - pad - 40} y={pad + 16 * i + 12} fill={c} fontSize={12}>
          {k}
        </text>
      ))}
    </svg>
  );
}
