// LIVE lane (optional, Pyodide): load the inlined lidar3dlab sources (public/pyodide/sources.json) and call
// lidar3dlab.live.run_trace_json for a bring-your-own-params interaction in the browser. This is a STUB — a real
// product wires Pyodide here. The replay path (App.tsx) is the always-available fallback (ADR-0054), so a product
// can ship with this lane dormant and still be fully functional.
import type { Trace } from '../lib/contract.types';

export interface LiveRequest {
  case_id?: string;
  params?: Record<string, number>;
  seed?: number;
}

export async function runLive(_req: LiveRequest): Promise<Trace> {
  throw new Error('live (Pyodide) lane not wired in the template example — replay is the fallback');
}
