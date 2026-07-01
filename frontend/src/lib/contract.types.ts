// CONTRACT 2 mirror (frontend side). MUST stay in lock-step with the Python schemas in
// data-pipeline/lidar3dlab/core/{trace.py, manifest.py}. A drift here makes `tsc` fail -> the contract is
// enforced at BUILD time (the web cannot ship reading a shape the pipeline does not produce).
//
// Domain: streaming 3D reconstruction. The trace is a baked, RGB-colored world point cloud + the camera
// trajectory; binary arrays are base64 (Float32 xyz / Uint8 rgb / Float32 poses) -> typed arrays in the viewer.

export interface PerFrame {
  idx: number;
  conf_mean: number;
  n_points: number;
  depth_min: number;
  depth_max: number;
}

export interface DepthThumb {
  idx: number;
  png_b64: string; // data:image/png;base64,...
}

export interface RefineInfo {
  refined: boolean;
  method?: string;
  voxel?: number;
  n_in?: number;
  n_out?: number;
  mesh_ready?: boolean;
  reason?: string;
}

export interface TraceSummary {
  n_points: number;
  n_frames: number;
  path_length_m: number;
}

export interface Trace {
  schema: string; // "lidar3d.recon/v1"
  case_id: string;
  n_frames: number;
  n_points: number;
  points_b64: string; // Float32 [n_points*3] world XYZ
  colors_b64: string; // Uint8   [n_points*3] RGB 0..255
  poses_b64: string;  // Float32 [n_frames*12] camera-to-world (row-major 3x4)
  per_frame: PerFrame[];
  frame_offsets?: number[]; // cumulative point count up to & including each frame (for progressive replay)
  path_length: number;
  bbox_min: number[];
  bbox_max: number[];
  depth_thumbs: DepthThumb[];
  refine: RefineInfo;
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

export interface EngineInfo {
  package: string;
  version: string;
  model: string;
  pretrained: boolean;
}

export interface CaseManifest {
  schema: string; // "lidar3d.manifest/v1"
  case_id: string;
  category: string;
  real_or_synthetic: string;
  expected_band: string;
  engine: EngineInfo;
  params: {
    source: string; // a label ("synthetic" or a sequence name), never an absolute path
    n_frames: number;
    max_frames: number;
    image_size: number;
    kv_window: number;
    scale_frames: number;
    decimation: number;
    conf_quantile: number;
  };
  seed: number;
  artifact: ArtifactRef;
  lane: 'live' | 'precompute';
  gate: GateVerdict;
  flags: Array<Record<string, string>>;
  refine: RefineInfo;
  metrics: Record<string, number | null | string | number[]>;
}

export interface CaseIndexEntry {
  case_id: string;
  category: string;
  manifest_path: string;
}

export interface CaseIndex {
  schema: string; // "lidar3d.index/v1"
  engine_version: string;
  n_cases: number;
  cases: CaseIndexEntry[];
}

// Decode a base64 payload into a typed array (browser).
export function b64ToF32(b64: string): Float32Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Float32Array(bytes.buffer);
}

export function b64ToU8(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}
