// The 3D reconstruction viewer. Decodes the baked artifact (CONTRACT 2) into a point cloud + the camera-frustum
// trajectory, and REPLAYS it: `reveal` (0..1) progressively unveils points frame by frame, `density` (stride)
// draws fewer points for a fluid response, `colorMode` toggles baked-RGB vs a LiDAR height ramp. `cameraMode`
// picks the navigation: orbit (third-person), first (from the current replay camera pose, follows the player),
// or top (bird's-eye). Render-on-demand only (no idle rAF); pauses on a hidden tab.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { b64ToF32, b64ToU8, type Trace } from '../lib/contract.types';

export type ColorMode = 'rgb' | 'depth';
export type CameraMode = 'orbit' | 'first' | 'top';

function ramp(t: number): [number, number, number] {
  const x = Math.max(0, Math.min(1, t)) * 4;
  const seg = [[30, 60, 160], [30, 180, 200], [60, 190, 90], [240, 210, 60], [220, 60, 50]];
  const i = Math.min(3, Math.floor(x)); const f = x - i; const a = seg[i], b = seg[i + 1];
  return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
}

export function CloudViewer({ trace, pointSize, dark, density, reveal, colorMode, cameraMode }:
  { trace: Trace; pointSize: number; dark: boolean; density: number; reveal: number; colorMode: ColorMode; cameraMode: CameraMode }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const api = useRef<any>(null);
  const data = useRef<{ pts: Float32Array; offsets: number[]; nFrames: number } | null>(null);
  const caseRef = useRef(''); // to re-fit the camera only on a NEW case, not on density/color changes

  useEffect(() => {
    const mount = mountRef.current!;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, 1, 0.001, 5000); // default +Y up; data is flipped to render frame
    // logarithmicDepthBuffer: a point cloud spans a wide depth range; a naive near/far destroys depth precision
    // and points VANISH when you zoom in close. This keeps them visible down to point level. preserveDrawingBuffer
    // keeps a settled static frame painted.
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, logarithmicDepthBuffer: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = false; controls.rotateSpeed = 0.75; controls.zoomSpeed = 1.1; controls.panSpeed = 0.8;
    controls.zoomToCursor = true; // zoom toward what you point at, so you can dive into a detail
    const cloud = new THREE.Points(new THREE.BufferGeometry(),
      new THREE.PointsMaterial({ size: pointSize, vertexColors: true, sizeAttenuation: true }));
    cloud.frustumCulled = false; // do NOT cull the whole cloud when the camera moves inside it (the "points
    // vanish when you zoom in" bug: three.js was culling the entire Points object by its bounding sphere).
    scene.add(cloud);
    const traj = new THREE.Group(); scene.add(traj);
    const grid = new THREE.GridHelper(20, 20, 0x274060, 0x18243c); grid.rotation.x = Math.PI / 2; scene.add(grid);
    const render = () => renderer.render(scene, camera);
    controls.addEventListener('change', render);
    const resize = () => {
      const w = mount.clientWidth || 800, h = mount.clientHeight || 520;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); render();
    };
    addEventListener('resize', resize);
    const ro = new ResizeObserver(() => resize()); ro.observe(mount);
    const onVis = () => { if (!document.hidden) render(); }; document.addEventListener('visibilitychange', onVis);
    api.current = {
      scene, camera, controls, cloud, traj, render, resize, centers: [], fwds: [], bbox: null,
      dispose: () => {
        controls.removeEventListener('change', render); removeEventListener('resize', resize); ro.disconnect();
        document.removeEventListener('visibilitychange', onVis); renderer.dispose(); mount.removeChild(renderer.domElement);
      },
    };
    resize();
    return () => api.current?.dispose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { if (api.current) { api.current.scene.background = new THREE.Color(dark ? 0x0b1020 : 0xeef2f8); api.current.render(); } }, [dark]);
  useEffect(() => { if (api.current) { (api.current.cloud.material as THREE.PointsMaterial).size = pointSize; api.current.render(); } }, [pointSize]);

  useEffect(() => {
    const a = api.current; if (!a || !trace) return;
    const pAll = b64ToF32(trace.points_b64), cAll = b64ToU8(trace.colors_b64);
    const nAll = (pAll.length / 3) | 0;
    const stride = Math.max(1, Math.round(density));
    const n = Math.ceil(nAll / stride);
    const pts = new Float32Array(n * 3), cols = new Uint8Array(n * 3);
    // OpenCV world (X-right, Y-down, Z-forward) -> render frame (Y-up): (x,y,z)->(x,-y,-z). Handedness-preserving
    // (a 180 deg rotation about X, det=+1), so NO mirror. The SAME transform is applied in DeckViewer.
    for (let i = 0, j = 0; i < nAll; i += stride, j++) {
      pts[j * 3] = pAll[i * 3]; pts[j * 3 + 1] = -pAll[i * 3 + 1]; pts[j * 3 + 2] = -pAll[i * 3 + 2];
      cols[j * 3] = cAll[i * 3]; cols[j * 3 + 1] = cAll[i * 3 + 1]; cols[j * 3 + 2] = cAll[i * 3 + 2];
    }
    if (colorMode === 'depth') {
      let lo = Infinity, hi = -Infinity;
      for (let j = 0; j < n; j++) { const y = pts[j * 3 + 1]; if (y < lo) lo = y; if (y > hi) hi = y; }
      const span = hi - lo || 1;
      for (let j = 0; j < n; j++) { const [r, g, b] = ramp(1 - (pts[j * 3 + 1] - lo) / span); cols[j * 3] = r; cols[j * 3 + 1] = g; cols[j * 3 + 2] = b; }
    }
    const g = a.cloud.geometry;
    g.setAttribute('position', new THREE.BufferAttribute(pts, 3));
    g.setAttribute('color', new THREE.BufferAttribute(cols, 3, true));
    g.computeBoundingBox();
    const rawOffsets = trace.frame_offsets && trace.frame_offsets.length > 1 ? trace.frame_offsets : null;
    const offsets = rawOffsets ? rawOffsets.map((o) => Math.ceil(o / stride)) : [];
    data.current = { pts, offsets, nFrames: trace.n_frames };

    a.traj.clear();
    const poses = b64ToF32(trace.poses_b64); const S = (poses.length / 12) | 0;
    // frustum size scales with the scene so the "camera cone" is visible at any scale (a fixed 0.05 looked like
    // a dot/line in a 19 m LiDAR corridor). Also scale by the mean inter-camera step so cones don't overlap.
    const diag = g.boundingBox ? g.boundingBox.getSize(new THREE.Vector3()).length() : 1;
    const s = Math.max(diag * 0.018, 0.03), d = s * 2.0;
    const fp = [[0,0,0],[s,s,d],[0,0,0],[s,-s,d],[0,0,0],[-s,s,d],[0,0,0],[-s,-s,d],[s,s,d],[s,-s,d],[s,-s,d],[-s,-s,d],[-s,-s,d],[-s,s,d],[-s,s,d],[s,s,d]];
    const FLIP = new THREE.Matrix4().makeScale(1, -1, -1); // OpenCV world -> render frame, applied AFTER the pose
    a.frustums = []; const centers: THREE.Vector3[] = []; const fwds: THREE.Vector3[] = [];
    for (let i = 0; i < S; i++) {
      const p = poses.subarray(i * 12, i * 12 + 12);
      const m = new THREE.Matrix4().set(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], 0, 0, 0, 1);
      centers.push(new THREE.Vector3(p[3], -p[7], -p[11]));                     // center in render frame
      fwds.push(new THREE.Vector3(p[2], -p[6], -p[10]).normalize());            // forward in render frame
      const fg = new THREE.BufferGeometry().setFromPoints(fp.map((q) => new THREE.Vector3(q[0], q[1], q[2])));
      fg.applyMatrix4(m); fg.applyMatrix4(FLIP);                                // pose then OpenCV->render flip
      const ls = new THREE.LineSegments(fg, new THREE.LineBasicMaterial({ color: 0x33d6a6 })); ls.frustumCulled = false; a.traj.add(ls); a.frustums.push(ls);
    }
    const tg = new THREE.BufferGeometry().setFromPoints(centers);
    a.trajLine = new THREE.Line(tg, new THREE.LineBasicMaterial({ color: 0xff5252 })); a.trajLine.frustumCulled = false; a.traj.add(a.trajLine);
    a.centers = centers; a.fwds = fwds; a.bbox = g.boundingBox;

    const isNewCase = caseRef.current !== trace.case_id; // preserve the user's view on density/color changes
    caseRef.current = trace.case_id;
    positionCamera(isNewCase);
    applyReveal(); a.resize();
    requestAnimationFrame(() => { a.resize(); requestAnimationFrame(() => a.resize()); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace, density, colorMode]);

  // place the camera per mode; `fit` re-fits orbit/top from scratch (used on load or mode switch)
  function positionCamera(fit: boolean) {
    const a = api.current, d = data.current; if (!a || !a.bbox || !a.centers.length) return;
    const bb: THREE.Box3 = a.bbox; const c = bb.getCenter(new THREE.Vector3());
    const r = Math.max(bb.getSize(new THREE.Vector3()).length() * 0.55, 0.5);
    const frame = d ? Math.min(a.centers.length - 1, Math.round(Math.max(0, Math.min(1, reveal)) * (a.centers.length - 1))) : 0;
    if (cameraMode === 'first') {
      const pos = a.centers[frame].clone(); const fwd = a.fwds[frame] || new THREE.Vector3(0, 0, 1);
      a.controls.target.copy(pos);                                    // CENTER on the last measured point
      a.camera.position.copy(pos.clone().addScaledVector(fwd, -r * 0.28)); // just behind the sensor, looking at it
      a.controls.minDistance = 0.01; a.controls.maxDistance = r * 6;
    } else if (cameraMode === 'top') {
      a.controls.target.copy(c);
      a.camera.position.copy(c.clone().add(new THREE.Vector3(0.001, r * 2.4, 0.001))); // above (+Y up)
      a.controls.minDistance = r * 0.2; a.controls.maxDistance = r * 8;
    } else if (fit) { // orbit, only re-fit on load / switch (don't yank the user's view every frame)
      a.controls.target.copy(c);
      a.camera.position.copy(c.clone().add(new THREE.Vector3(0.5, 0.45, 1).normalize().multiplyScalar(r * 2.2)));
      a.controls.minDistance = r * 0.05; a.controls.maxDistance = r * 10;
    }
    a.controls.update(); a.render();
  }
  useEffect(() => { positionCamera(true); /* eslint-disable-next-line */ }, [cameraMode]);

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
    if (cameraMode === 'first') positionCamera(false); // follow the player from the camera POV
    a.render();
  }
  useEffect(applyReveal, [reveal]);

  return <div ref={mountRef} style={{ width: '100%', height: '100%', minHeight: 420 }} />;
}
