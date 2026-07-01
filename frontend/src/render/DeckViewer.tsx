// A deck.gl point-cloud viewer: GPU-instanced PointCloudLayer (scales to millions) + the camera trajectory +
// the per-frame observer frustums, all revealed GPU-side by DataFilterExtension (replay costs nothing per
// frame). Controlled viewState so mouse interaction AND the camera-mode buttons work; the view is preserved on
// density/color changes and only re-fit on a new case or a camera-mode switch. Same prop interface as CloudViewer.
import { useEffect, useRef } from 'react';
import { COORDINATE_SYSTEM, Deck, OrbitView } from '@deck.gl/core';
import { LineLayer, PointCloudLayer } from '@deck.gl/layers';
import { DataFilterExtension } from '@deck.gl/extensions';
import { b64ToF32, b64ToU8, type Trace } from '../lib/contract.types';
import type { CameraMode, ColorMode } from './CloudViewer';

function ramp(t: number): [number, number, number] {
  const x = Math.max(0, Math.min(1, t)) * 4;
  const seg = [[30, 60, 160], [30, 180, 200], [60, 190, 90], [240, 210, 60], [220, 60, 50]];
  const i = Math.min(3, Math.floor(x)); const f = x - i; const a = seg[i], b = seg[i + 1];
  return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
}
type V3 = [number, number, number];
const apply = (p: Float32Array, o: number, x: number, y: number, z: number): V3 =>
  [p[o] * x + p[o + 1] * y + p[o + 2] * z + p[o + 3], p[o + 4] * x + p[o + 5] * y + p[o + 6] * z + p[o + 7], p[o + 8] * x + p[o + 9] * y + p[o + 10] * z + p[o + 11]];

export function DeckViewer({ trace, pointSize, dark, density, reveal, colorMode, cameraMode, showCones = true, showTraj = true }:
  { trace: Trace; pointSize: number; dark: boolean; density: number; reveal: number; colorMode: ColorMode; cameraMode: CameraMode; showCones?: boolean; showTraj?: boolean }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const deckRef = useRef<any>(null);
  const vsRef = useRef<any>(null);
  const caseRef = useRef('');
  const data = useRef<any>(null);

  // build the strided/colored cloud + trajectory segments + per-frame frustum segments (each carries its frame index)
  useEffect(() => {
    if (!trace) return;
    const pAll = b64ToF32(trace.points_b64), cAll = b64ToU8(trace.colors_b64);
    const nAll = (pAll.length / 3) | 0, stride = Math.max(1, Math.round(density));
    const n = Math.ceil(nAll / stride);
    const pos = new Float32Array(n * 3), col = new Uint8Array(n * 3), fil = new Float32Array(n);
    let lo = Infinity, hi = -Infinity, minx = Infinity, miny = Infinity, minz = Infinity, maxx = -Infinity, maxy = -Infinity, maxz = -Infinity;
    // NEGATE Y: the cloud is Y-down (OpenCV); deck.gl OrbitView treats +Y as up, so without this the scene
    // renders vertically flipped vs three.js (which sets camera.up = -Y). Flip once, here, consistently.
    for (let i = 0, j = 0; i < nAll; i += stride, j++) {
      const x = pAll[i * 3], y = -pAll[i * 3 + 1], z = pAll[i * 3 + 2];
      pos[j * 3] = x; pos[j * 3 + 1] = y; pos[j * 3 + 2] = z;
      col[j * 3] = cAll[i * 3]; col[j * 3 + 1] = cAll[i * 3 + 1]; col[j * 3 + 2] = cAll[i * 3 + 2]; fil[j] = j;
      if (y < lo) lo = y; if (y > hi) hi = y;
      if (x < minx) minx = x; if (y < miny) miny = y; if (z < minz) minz = z;
      if (x > maxx) maxx = x; if (y > maxy) maxy = y; if (z > maxz) maxz = z;
    }
    if (colorMode === 'depth') { const span = hi - lo || 1; for (let j = 0; j < n; j++) { const [r, g, b] = ramp(1 - (pos[j * 3 + 1] - lo) / span); col[j * 3] = r; col[j * 3 + 1] = g; col[j * 3 + 2] = b; } }
    const center: V3 = [(minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2];
    const radius = Math.max(Math.hypot(maxx - minx, maxy - miny, maxz - minz) * 0.5, 0.5);

    // poses -> centers, forwards, trajectory segments, frustum segments (with per-item frame index for reveal)
    const poses = b64ToF32(trace.poses_b64); const S = (poses.length / 12) | 0;
    const centers: V3[] = [], fwds: V3[] = [];
    const traj: { s: V3; t: V3; f: number }[] = [], frus: { s: V3; t: V3; f: number }[] = [];
    const off = trace.frame_offsets && trace.frame_offsets.length > 1 ? trace.frame_offsets.map((o) => Math.ceil(o / stride)) : [];
    const sz = Math.max(radius * 0.02, 0.03), dd = sz * 2;
    const corners: V3[] = [[sz, sz, dd], [sz, -sz, dd], [-sz, -sz, dd], [-sz, sz, dd]];
    for (let i = 0; i < S; i++) {
      const o = i * 12;
      const c: V3 = [poses[o + 3], -poses[o + 7], poses[o + 11]];   // Y negated to match the cloud
      centers.push(c);
      fwds.push([poses[o + 2], -poses[o + 6], poses[o + 10]]);
      const cw = corners.map((q) => { const p = apply(poses, o, q[0], q[1], q[2]); return [p[0], -p[1], p[2]] as V3; });
      for (let k = 0; k < 4; k++) { frus.push({ s: c, t: cw[k], f: i }); frus.push({ s: cw[k], t: cw[(k + 1) % 4], f: i }); }
      if (i > 0) traj.push({ s: centers[i - 1], t: c, f: i });
    }
    data.current = { pos, col, fil, n, center, radius, centers, fwds, traj, frus, off, nFrames: trace.n_frames };
    const isNew = caseRef.current !== trace.case_id;
    caseRef.current = trace.case_id;
    ensureDeck();
    redraw(isNew);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace, density, colorMode]);

  useEffect(() => { redraw(true); /* re-fit on camera-mode switch */ }, [cameraMode]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { redraw(cameraMode === 'first'); /* FP follows the player; others keep the view */ }, [reveal]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { redraw(false); }, [pointSize, dark, showCones, showTraj]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { deckRef.current?.finalize?.(); deckRef.current = null; }, []);

  function revealFrames(): number {
    const d = data.current; if (!d) return 0;
    return Math.max(1, Math.round(Math.max(0, Math.min(1, reveal)) * ((d.nFrames || 1) - 1)) + 1);
  }
  function revealPts(): number {
    const d = data.current; if (!d) return 0;
    const rev = Math.max(0, Math.min(1, reveal));
    if (d.off.length) { const fi = Math.min(d.off.length - 1, Math.floor(rev * (d.off.length - 1))); return d.off[fi]; }
    return Math.floor(rev * d.n);
  }

  function computeVS() {
    const d = data.current; if (!d) return { target: [0, 0, 0], zoom: 0 };
    const zoom = Math.log2(240 / d.radius);
    if (cameraMode === 'top') return { target: d.center, rotationOrbit: 0, rotationX: 89, zoom, minZoom: -6, maxZoom: 24 };
    if (cameraMode === 'first') {
      const f = Math.min(d.centers.length - 1, Math.round(Math.max(0, Math.min(1, reveal)) * (d.centers.length - 1)));
      return { target: d.centers[f] || d.center, rotationOrbit: -25, rotationX: 14, zoom: Math.log2(240 / (d.radius * 0.3)), minZoom: -6, maxZoom: 26 };
    }
    return { target: d.center, rotationOrbit: 30, rotationX: 22, zoom, minZoom: -6, maxZoom: 24 };
  }

  function ensureDeck() {
    if (deckRef.current || !wrapRef.current) return;
    vsRef.current = computeVS();
    deckRef.current = new Deck({
      parent: wrapRef.current,
      views: new OrbitView({ orbitAxis: 'Y', fovy: 55 }),
      controller: { inertia: true },
      viewState: vsRef.current,
      onViewStateChange: ({ viewState }: any) => { vsRef.current = viewState; deckRef.current?.setProps({ viewState }); },
    });
  }

  function redraw(resetView: boolean) {
    const d = data.current; if (!d || !deckRef.current) return;
    const rf = revealFrames();
    const ext = [new DataFilterExtension({ filterSize: 1 })];
    const layers: any[] = [
      new PointCloudLayer({
        id: 'cloud', coordinateSystem: COORDINATE_SYSTEM.CARTESIAN, pointSize: Math.max(1, pointSize * 150),
        data: { length: d.n, attributes: { getPosition: { value: d.pos, size: 3 }, getColor: { value: d.col, size: 3, normalized: true } } },
        getFilterValue: (_: unknown, o: { index: number }) => o.index, filterRange: [0, Math.max(1, revealPts())], extensions: ext,
      }),
      ...(showTraj ? [new LineLayer({
        id: 'traj', coordinateSystem: COORDINATE_SYSTEM.CARTESIAN, data: d.traj, getWidth: 2.5,
        getSourcePosition: (o: any) => o.s, getTargetPosition: (o: any) => o.t, getColor: [255, 82, 82],
        getFilterValue: (o: any) => o.f, filterRange: [0, rf], extensions: ext,
      })] : []),
      ...(showCones ? [new LineLayer({
        id: 'frustums', coordinateSystem: COORDINATE_SYSTEM.CARTESIAN, data: d.frus, getWidth: 1.5,
        getSourcePosition: (o: any) => o.s, getTargetPosition: (o: any) => o.t, getColor: [51, 214, 166],
        getFilterValue: (o: any) => o.f, filterRange: [0, rf], extensions: ext,
      })] : []),
    ];
    const props: any = { layers };
    if (resetView) { vsRef.current = computeVS(); props.viewState = vsRef.current; }
    deckRef.current.setProps(props);
  }

  return <div ref={wrapRef} style={{ position: 'relative', width: '100%', height: '100%', minHeight: 420, background: dark ? '#0b1020' : '#eef2f8' }} />;
}
