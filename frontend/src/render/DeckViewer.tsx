// A deck.gl point-cloud viewer: GPU-instanced PointCloudLayer that scales to millions, with progressive replay
// done GPU-side (DataFilterExtension filters points by their order index vs the revealed count, so replay costs
// nothing per frame). Same prop interface as the three.js CloudViewer, so the App can switch renderers. Reveal,
// density (draw-stride), colorMode (RGB / LiDAR height ramp) and cameraMode (orbit / first-person / top).
import { useEffect, useRef } from 'react';
import { COORDINATE_SYSTEM, Deck, OrbitView } from '@deck.gl/core';
import { PointCloudLayer } from '@deck.gl/layers';
import { DataFilterExtension } from '@deck.gl/extensions';
import { b64ToF32, b64ToU8, type Trace } from '../lib/contract.types';
import type { CameraMode, ColorMode } from './CloudViewer';

function ramp(t: number): [number, number, number] {
  const x = Math.max(0, Math.min(1, t)) * 4;
  const seg = [[30, 60, 160], [30, 180, 200], [60, 190, 90], [240, 210, 60], [220, 60, 50]];
  const i = Math.min(3, Math.floor(x)); const f = x - i; const a = seg[i], b = seg[i + 1];
  return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
}

export function DeckViewer({ trace, pointSize, dark, density, reveal, colorMode, cameraMode }:
  { trace: Trace; pointSize: number; dark: boolean; density: number; reveal: number; colorMode: ColorMode; cameraMode: CameraMode }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const deckRef = useRef<any>(null);
  const dataRef = useRef<{ pos: Float32Array; col: Uint8Array; fil: Float32Array; n: number;
    center: [number, number, number]; radius: number; offsets: number[]; centers: number[][]; nFrames: number } | null>(null);

  // (re)build the strided/colored binary buffers on trace / density / colorMode change
  useEffect(() => {
    if (!trace) return;
    const pAll = b64ToF32(trace.points_b64), cAll = b64ToU8(trace.colors_b64);
    const nAll = (pAll.length / 3) | 0;
    const stride = Math.max(1, Math.round(density));
    const n = Math.ceil(nAll / stride);
    const pos = new Float32Array(n * 3), col = new Uint8Array(n * 3), fil = new Float32Array(n);
    let lo = Infinity, hi = -Infinity;
    for (let i = 0, j = 0; i < nAll; i += stride, j++) {
      pos[j * 3] = pAll[i * 3]; pos[j * 3 + 1] = pAll[i * 3 + 1]; pos[j * 3 + 2] = pAll[i * 3 + 2];
      col[j * 3] = cAll[i * 3]; col[j * 3 + 1] = cAll[i * 3 + 1]; col[j * 3 + 2] = cAll[i * 3 + 2];
      fil[j] = j;
      const y = pos[j * 3 + 1]; if (y < lo) lo = y; if (y > hi) hi = y;
    }
    if (colorMode === 'depth') {
      const span = hi - lo || 1;
      for (let j = 0; j < n; j++) { const [r, g, b] = ramp(1 - (pos[j * 3 + 1] - lo) / span); col[j * 3] = r; col[j * 3 + 1] = g; col[j * 3 + 2] = b; }
    }
    // bbox
    let minx = Infinity, miny = Infinity, minz = Infinity, maxx = -Infinity, maxy = -Infinity, maxz = -Infinity;
    for (let j = 0; j < n; j++) {
      const x = pos[j * 3], y = pos[j * 3 + 1], z = pos[j * 3 + 2];
      if (x < minx) minx = x; if (y < miny) miny = y; if (z < minz) minz = z;
      if (x > maxx) maxx = x; if (y > maxy) maxy = y; if (z > maxz) maxz = z;
    }
    const center: [number, number, number] = [(minx + maxx) / 2, (miny + maxy) / 2, (minz + maxz) / 2];
    const radius = Math.max(Math.hypot(maxx - minx, maxy - miny, maxz - minz) * 0.5, 0.5);
    const poses = b64ToF32(trace.poses_b64); const S = (poses.length / 12) | 0;
    const centers: number[][] = [];
    for (let i = 0; i < S; i++) centers.push([poses[i * 12 + 3], poses[i * 12 + 7], poses[i * 12 + 11]]);
    const rawOffsets = trace.frame_offsets && trace.frame_offsets.length > 1 ? trace.frame_offsets : [];
    const offsets = rawOffsets.map((o) => Math.ceil(o / stride));
    dataRef.current = { pos, col, fil, n, center, radius, offsets, centers, nFrames: trace.n_frames };
    render(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace, density, colorMode]);

  useEffect(() => render(false), [reveal, cameraMode, pointSize, dark]); // eslint-disable-line react-hooks/exhaustive-deps

  function revealCount(): number {
    const d = dataRef.current; if (!d) return 0;
    const rev = Math.max(0, Math.min(1, reveal));
    if (d.offsets.length) { const fi = Math.min(d.offsets.length - 1, Math.floor(rev * (d.offsets.length - 1))); return d.offsets[fi]; }
    return Math.floor(rev * d.n);
  }

  function viewState() {
    const d = dataRef.current; if (!d) return {};
    const zoom = Math.log2(220 / d.radius);
    if (cameraMode === 'top') return { target: d.center, rotationOrbit: 0, rotationX: 90, zoom, minZoom: -5, maxZoom: 20 };
    if (cameraMode === 'first') {
      const f = Math.min(d.centers.length - 1, Math.round(Math.max(0, Math.min(1, reveal)) * (d.centers.length - 1)));
      const c = d.centers[f] || d.center;
      return { target: c, rotationOrbit: -20, rotationX: 12, zoom: Math.log2(220 / (d.radius * 0.25)), minZoom: -5, maxZoom: 24 };
    }
    return { target: d.center, rotationOrbit: 25, rotationX: 20, zoom, minZoom: -5, maxZoom: 22 };
  }

  function render(resetView: boolean) {
    const d = dataRef.current; if (!d || !wrapRef.current) return;
    const shown = revealCount();
    const layer = new PointCloudLayer({
      id: 'cloud',
      data: { length: d.n, attributes: {
        getPosition: { value: d.pos, size: 3 },
        getColor: { value: d.col, size: 3, normalized: true },
        getFilterValue: { value: d.fil, size: 1 },
      } },
      coordinateSystem: COORDINATE_SYSTEM.CARTESIAN,
      pointSize: Math.max(1, pointSize * 260),
      getFilterValue: (_: unknown, o: { index: number }) => o.index,
      filterRange: [0, Math.max(1, shown)],
      extensions: [new DataFilterExtension({ filterSize: 1 })],
      updateTriggers: {},
    });
    const props: any = {
      views: new OrbitView({ orbitAxis: 'Y', fovy: 55 }),
      controller: { inertia: true },
      layers: [layer],
      parameters: { clearColor: dark ? [0.043, 0.063, 0.125, 1] : [0.93, 0.95, 0.97, 1] },
    };
    if (resetView || !deckRef.current) props.initialViewState = viewState();
    else props.viewState = undefined; // let the controller keep the user's view during replay
    if (!deckRef.current) {
      deckRef.current = new Deck({ parent: wrapRef.current, ...props, initialViewState: viewState() });
    } else {
      deckRef.current.setProps(resetView ? { ...props, initialViewState: viewState() } : { layers: [layer], parameters: props.parameters });
    }
  }

  useEffect(() => () => { deckRef.current?.finalize(); deckRef.current = null; }, []);

  return <div ref={wrapRef} style={{ position: 'relative', width: '100%', height: '100%', minHeight: 420 }} />;
}
