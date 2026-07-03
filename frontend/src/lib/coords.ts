// Single source of truth for the world -> render-frame coordinate transform, shared by ALL renderers
// (three.js CloudViewer, surfels, Potree, deck.gl). Every renderer MUST use these helpers instead of
// inlining `(x, -y, -z)`, so the four renderers can never drift apart and the mapping is unit-tested.
//
// OpenCV world (the baked artifact / CONTRACT 2): X-right, Y-DOWN, Z-FORWARD (into the scene).
// Render frame (what the viewers draw, Y-up): X-right, Y-UP, Z-BACK.
// The map is (x, y, z) -> (x, -y, -z): a 180 degree rotation about the X axis. Its determinant is +1, so it
// is HANDEDNESS-PRESERVING (a rotation, NOT a mirror). This is why the reconstruction is not flipped.

export type Vec3 = [number, number, number];

/** Map a single world point (OpenCV frame) into the render frame. The one place `(x,-y,-z)` is written. */
export function worldToRender(x: number, y: number, z: number): Vec3 {
  return [x, -y, -z];
}

/**
 * Batch version for the hot per-point cloud path: reads world points (Float32 [n*3]) with an optional
 * stride and writes render-frame points into a fresh Float32Array. No per-point allocation, so renderers
 * get the shared transform without the cost of calling worldToRender() millions of times.
 */
export function worldToRenderBuffer(worldPts: ArrayLike<number>, stride = 1): Float32Array {
  const n = (worldPts.length / 3) | 0;
  const st = Math.max(1, Math.floor(stride));
  const m = Math.ceil(n / st);
  const out = new Float32Array(m * 3);
  for (let i = 0, j = 0; i < n; i += st, j++) {
    out[j * 3] = worldPts[i * 3];
    out[j * 3 + 1] = -worldPts[i * 3 + 1];
    out[j * 3 + 2] = -worldPts[i * 3 + 2];
  }
  return out;
}

// A camera pose is a row-major 3x4 camera-to-world matrix stored as 12 floats at offset `o`:
//   [ r00 r01 r02 tx | r10 r11 r12 ty | r20 r21 r22 tz ]
// column 3 (indices o+3,o+7,o+11) is the camera centre; column 2 (o+2,o+6,o+10) is the camera forward (+Z).

/** Camera centre (translation) of a pose, in the render frame. */
export function poseCenter(p: ArrayLike<number>, o = 0): Vec3 {
  return worldToRender(p[o + 3], p[o + 7], p[o + 11]);
}

/** Unit camera-forward (+Z axis of the pose) of a pose, in the render frame. */
export function poseForward(p: ArrayLike<number>, o = 0): Vec3 {
  const [fx, fy, fz] = worldToRender(p[o + 2], p[o + 6], p[o + 10]);
  const n = Math.hypot(fx, fy, fz) || 1;
  return [fx / n, fy / n, fz / n];
}

/** Transform a camera-local point (e.g. a frustum corner) by the pose, then into the render frame. */
export function poseApplyToRender(p: ArrayLike<number>, o: number, lx: number, ly: number, lz: number): Vec3 {
  const wx = p[o] * lx + p[o + 1] * ly + p[o + 2] * lz + p[o + 3];
  const wy = p[o + 4] * lx + p[o + 5] * ly + p[o + 6] * lz + p[o + 7];
  const wz = p[o + 8] * lx + p[o + 9] * ly + p[o + 10] * lz + p[o + 11];
  return worldToRender(wx, wy, wz);
}

// ---- OBB diagnostic ---------------------------------------------------------------------------------
// An axis-aligned bounding box of the FINAL cloud, computed once in the render frame from the shared
// transform, and drawn by every renderer. If the box hugs the cloud identically in all four, the
// coordinate systems agree and any remaining difference is pure camera/view setup; if a renderer's box
// is mirrored/rotated relative to its cloud, that renderer has a real transform bug. The RGB axis triad
// (see obbAxes) removes the box's mirror ambiguity so orientation is unambiguous across renderers.

export interface Obb {
  min: Vec3;
  max: Vec3;
  center: Vec3;
  size: Vec3;
  corners: Vec3[]; // 8 corners, in the render frame
  edges: Array<[number, number]>; // 12 edges as index pairs into `corners`
}

// corner index = bit0:x(min/max) bit1:y(min/max) bit2:z(min/max)
const OBB_EDGES: Array<[number, number]> = [
  [0, 1], [1, 3], [3, 2], [2, 0], // z = min face
  [4, 5], [5, 7], [7, 6], [6, 4], // z = max face
  [0, 4], [1, 5], [2, 6], [3, 7], // z pillars
];

/** Axis-aligned bounding box (render frame) of the world cloud `worldPts` (Float32 [n*3]). */
export function cloudObbRender(worldPts: ArrayLike<number>, stride = 1): Obb {
  const n = (worldPts.length / 3) | 0;
  const st = Math.max(1, Math.floor(stride));
  let minx = Infinity, miny = Infinity, minz = Infinity;
  let maxx = -Infinity, maxy = -Infinity, maxz = -Infinity;
  for (let i = 0; i < n; i += st) {
    const [x, y, z] = worldToRender(worldPts[i * 3], worldPts[i * 3 + 1], worldPts[i * 3 + 2]);
    if (x < minx) minx = x; if (y < miny) miny = y; if (z < minz) minz = z;
    if (x > maxx) maxx = x; if (y > maxy) maxy = y; if (z > maxz) maxz = z;
  }
  const min: Vec3 = [minx, miny, minz];
  const max: Vec3 = [maxx, maxy, maxz];
  const corners: Vec3[] = [];
  for (let b = 0; b < 8; b++) {
    corners.push([b & 1 ? maxx : minx, b & 2 ? maxy : miny, b & 4 ? maxz : minz]);
  }
  return {
    min,
    max,
    center: [(minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2],
    size: [maxx - minx, maxy - miny, maxz - minz],
    corners,
    edges: OBB_EDGES,
  };
}

export interface ObbAxes {
  origin: Vec3;
  x: Vec3; // tip of the +X (render) axis, drawn RED
  y: Vec3; // +Y, drawn GREEN
  z: Vec3; // +Z, drawn BLUE
  len: number;
}

/** A short RGB axis triad at the OBB min corner, to disambiguate the box's orientation across renderers. */
export function obbAxes(obb: Obb, frac = 0.25): ObbAxes {
  const len = Math.max(Math.hypot(obb.size[0], obb.size[1], obb.size[2]) * frac, 1e-3);
  const o = obb.min;
  return {
    origin: o,
    x: [o[0] + len, o[1], o[2]],
    y: [o[0], o[1] + len, o[2]],
    z: [o[0], o[1], o[2] + len],
    len,
  };
}
