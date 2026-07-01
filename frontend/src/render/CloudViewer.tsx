// The 3D reconstruction viewer. Decodes the baked artifact (CONTRACT 2) into a point cloud + the camera-frustum
// trajectory, and REPLAYS it: `reveal` (0..1) progressively unveils points frame by frame (the "watch the data
// flow build" idea), `density` (stride) draws fewer points for a fluid response, `colorMode` toggles baked-RGB
// (camera texture) vs a height ramp (LiDAR-depth view). Render-on-demand only (no idle rAF) so an unattended tab
// burns zero CPU; pauses on a hidden tab.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { b64ToF32, b64ToU8, type Trace } from '../lib/contract.types';

export type ColorMode = 'rgb' | 'depth';

// perceptual blue->cyan->green->yellow->red ramp for the LiDAR-depth view (t in 0..1)
function ramp(t: number): [number, number, number] {
  const x = Math.max(0, Math.min(1, t)) * 4;
  const seg = [[30, 60, 160], [30, 180, 200], [60, 190, 90], [240, 210, 60], [220, 60, 50]];
  const i = Math.min(3, Math.floor(x)); const f = x - i; const a = seg[i], b = seg[i + 1];
  return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
}

export function CloudViewer({ trace, pointSize, dark, density, reveal, colorMode }:
  { trace: Trace; pointSize: number; dark: boolean; density: number; reveal: number; colorMode: ColorMode }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const api = useRef<any>(null);
  const data = useRef<{ pts: Float32Array; offsets: number[]; nFrames: number } | null>(null);

  useEffect(() => {
    const mount = mountRef.current!;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, 1, 0.001, 5000);
    camera.up.set(0, -1, 0);
    // preserveDrawingBuffer: with render-on-demand a single static frame would otherwise be discarded before
    // compositing (blank canvas until the next draw); keep it so idle/settled frames stay painted.
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = false;
    const cloud = new THREE.Points(new THREE.BufferGeometry(),
      new THREE.PointsMaterial({ size: pointSize, vertexColors: true, sizeAttenuation: true }));
    scene.add(cloud);
    const traj = new THREE.Group(); scene.add(traj);
    const grid = new THREE.GridHelper(20, 20, 0x274060, 0x18243c); grid.rotation.x = Math.PI / 2; scene.add(grid);
    const render = () => renderer.render(scene, camera);
    const resize = () => {
      const w = mount.clientWidth || 800, h = mount.clientHeight || 520;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); render();
    };
    controls.addEventListener('change', render); addEventListener('resize', resize);
    const onVis = () => { if (!document.hidden) render(); }; document.addEventListener('visibilitychange', onVis);
    // repaint when the flex container finally gets its real size (render-on-demand + late layout would else stay blank)
    const ro = new ResizeObserver(() => resize()); ro.observe(mount);
    api.current = { scene, camera, controls, cloud, traj, render, resize, dispose: () => {
      controls.removeEventListener('change', render); removeEventListener('resize', resize); ro.disconnect();
      document.removeEventListener('visibilitychange', onVis); renderer.dispose(); mount.removeChild(renderer.domElement);
    } };
    resize();
    return () => api.current?.dispose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { if (api.current) { api.current.scene.background = new THREE.Color(dark ? 0x0b1020 : 0xeef2f8); api.current.render(); } }, [dark]);
  useEffect(() => { if (api.current) { (api.current.cloud.material as THREE.PointsMaterial).size = pointSize; api.current.render(); } }, [pointSize]);

  // decode + build a DENSITY-strided buffer (fewer points = fluid); color = baked RGB or a height ramp (LiDAR depth)
  useEffect(() => {
    const a = api.current; if (!a || !trace) return;
    const pAll = b64ToF32(trace.points_b64), cAll = b64ToU8(trace.colors_b64);
    const nAll = (pAll.length / 3) | 0;
    const stride = Math.max(1, Math.round(density));
    const n = Math.ceil(nAll / stride);
    const pts = new Float32Array(n * 3), cols = new Uint8Array(n * 3);
    for (let i = 0, j = 0; i < nAll; i += stride, j++) {
      pts[j * 3] = pAll[i * 3]; pts[j * 3 + 1] = pAll[i * 3 + 1]; pts[j * 3 + 2] = pAll[i * 3 + 2];
      cols[j * 3] = cAll[i * 3]; cols[j * 3 + 1] = cAll[i * 3 + 1]; cols[j * 3 + 2] = cAll[i * 3 + 2];
    }
    if (colorMode === 'depth') { // color by height (up = -Y): higher = warmer
      let lo = Infinity, hi = -Infinity;
      for (let j = 0; j < n; j++) { const y = pts[j * 3 + 1]; if (y < lo) lo = y; if (y > hi) hi = y; }
      const span = hi - lo || 1;
      for (let j = 0; j < n; j++) {
        const [r, g, b] = ramp(1 - (pts[j * 3 + 1] - lo) / span); cols[j * 3] = r; cols[j * 3 + 1] = g; cols[j * 3 + 2] = b;
      }
    }
    const g = a.cloud.geometry;
    g.setAttribute('position', new THREE.BufferAttribute(pts, 3));
    g.setAttribute('color', new THREE.BufferAttribute(cols, 3, true));
    g.computeBoundingBox();
    const rawOffsets = trace.frame_offsets && trace.frame_offsets.length > 1 ? trace.frame_offsets : null;
    const offsets = rawOffsets ? rawOffsets.map((o) => Math.ceil(o / stride)) : [];
    data.current = { pts, offsets, nFrames: trace.n_frames };

    // trajectory frustums (all frames; revealed progressively)
    a.traj.clear();
    const poses = b64ToF32(trace.poses_b64); const S = (poses.length / 12) | 0;
    a.frustums = []; const centers: number[] = [];
    for (let i = 0; i < S; i++) {
      const p = poses.subarray(i * 12, i * 12 + 12);
      const m = new THREE.Matrix4().set(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], 0, 0, 0, 1);
      centers.push(p[3], p[7], p[11]);
      const s = 0.05, d = 0.09; const fp = [[0,0,0],[s,s,d],[0,0,0],[s,-s,d],[0,0,0],[-s,s,d],[0,0,0],[-s,-s,d],[s,s,d],[s,-s,d],[s,-s,d],[-s,-s,d],[-s,-s,d],[-s,s,d],[-s,s,d],[s,s,d]];
      const fg = new THREE.BufferGeometry().setFromPoints(fp.map((q) => new THREE.Vector3(q[0], q[1], q[2]))); fg.applyMatrix4(m);
      const ls = new THREE.LineSegments(fg, new THREE.LineBasicMaterial({ color: 0x33d6a6 })); a.traj.add(ls); a.frustums.push(ls);
    }
    const tg = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(centers, 3));
    a.trajLine = new THREE.Line(tg, new THREE.LineBasicMaterial({ color: 0xff5252 })); a.traj.add(a.trajLine);

    const bb = g.boundingBox!; const c = bb.getCenter(new THREE.Vector3());
    const r = Math.max(bb.getSize(new THREE.Vector3()).length() * 0.55, 0.5);
    a.controls.target.copy(c);
    a.camera.position.copy(c.clone().add(new THREE.Vector3(0.4, -0.5, -1).normalize().multiplyScalar(r * 2.2)));
    a.controls.update();
    applyReveal(); a.resize(); // resize() sizes the canvas to the settled layout, then renders
    // the very first frame after a WebGL context is created can composite empty; kick two more paints
    requestAnimationFrame(() => { a.resize(); requestAnimationFrame(() => a.resize()); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace, density, colorMode]);

  function applyReveal() {
    const a = api.current, d = data.current; if (!a || !d) return;
    const nPts = (d.pts.length / 3) | 0;
    const rev = Math.max(0, Math.min(1, reveal));
    let shownPts: number, shownFrames: number;
    if (d.offsets.length) {
      const fi = Math.min(d.offsets.length - 1, Math.floor(rev * (d.offsets.length - 1)));
      shownPts = d.offsets[fi]; shownFrames = fi + 1;
    } else {
      shownPts = Math.floor(rev * nPts); shownFrames = Math.ceil(rev * d.nFrames);
    }
    a.cloud.geometry.setDrawRange(0, Math.max(0, shownPts));
    if (a.trajLine) a.trajLine.geometry.setDrawRange(0, Math.max(2, shownFrames));
    if (a.frustums) a.frustums.forEach((f: THREE.LineSegments, i: number) => { f.visible = i < shownFrames; });
    a.render();
  }
  useEffect(applyReveal, [reveal]);

  return <div ref={mountRef} style={{ width: '100%', height: '100%', minHeight: 420 }} />;
}
