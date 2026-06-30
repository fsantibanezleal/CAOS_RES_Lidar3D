// CONTRACT 2 mirror (frontend side). MUST stay in lock-step with the Python schemas in
// data-pipeline/lidar3dlab/core/{trace.py, manifest.py}. A drift here makes `tsc` fail -> the contract is
// enforced at BUILD time (the web cannot ship reading a shape the pipeline does not produce).

export interface TraceSummary {
  peak_I: number;
  t_peak: number;
  attack_rate: number;
}

export interface Trace {
  schema: string; // "example.trace/v1"
  case_id: string;
  t: number[];
  S: number[];
  I: number[];
  R: number[];
  summary: TraceSummary;
}

export interface ArtifactRef {
  path: string;
  format: string;
  trace_schema: string;
  bytes: number;
}

export interface GateVerdict {
  lane: string;
  pure_python: boolean;
  wheels: string[];
  trace_bytes: number;
  run_ms_budget: number;
  trace_bytes_budget: number;
  reasons: string[];
}

export interface CaseManifest {
  schema: string; // "example.manifest/v2"
  case_id: string;
  category: string;
  real_or_synthetic: string;
  expected_band: string;
  engine: { package: string; version: string; model: string };
  params: Record<string, number>;
  seed: number;
  artifact: ArtifactRef;
  lane: 'live' | 'precompute';
  gate: GateVerdict;
  flags: Array<Record<string, string>>;
  metrics: Record<string, number>;
}

export interface CaseIndexEntry {
  case_id: string;
  category: string;
  manifest_path: string;
}

export interface CaseIndex {
  schema: string; // "example.index/v1"
  engine_version: string;
  n_cases: number;
  cases: CaseIndexEntry[];
}
