// The 3D reconstruction viewer. Decodes the baked artifact (CONTRACT 2) into a point cloud + the camera-frustum
// trajectory, and REPLAYS it: `reveal` (0..1) progressively unveils points frame by frame, `density` (stride)
// draws fewer points for a fluid response, `colorMode` toggles baked-RGB vs a LiDAR height ramp. `cameraMode`
// picks the navigation: orbit (third-person), first (from the current replay camera pose, follows the player),
// or top (bird's-eye). Render-on-demand only (no idle rAF); pauses on a hidden tab.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { b64ToF32, b64ToU8, type Trace } from '../lib/contract.types';
import { worldToRenderBuffer, poseCenter, poseForward, poseApplyToRender, cloudObbRender, obbAxes } from '../lib/coords';

export type ColorMode = 'rgb' | 'depth';
export type CameraMode = 'orbit' | 'first' | 'top';

// a soft round sprite so points render as discs that merge into a surface (the "surfels" method), not squares
let _disc: THREE.Texture | null = null;
function discTexture(): THREE.Texture {
  if (_disc) return _disc;
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d')!; const rad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  rad.addColorStop(0, 'rgba(255,255,255,1)'); rad.addColorStop(0.7, 'rgba(255,255,255,1)'); rad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rad; g.beginPath(); g.arc(32, 32, 32, 0, Math.PI * 2); g.fill();
  _disc = new THREE.CanvasTexture(c); return _disc;
}

function ramp(t: number): [number, number, number] {
  const x = Math.max(0, Math.min(1, t)) * 4;
  const seg = [[30, 60, 160], [30, 180, 200], [60, 190, 90], [240, 210, 60], [220, 60, 50]];
  const i = Math.min(3, Math.floor(x)); const f = x - i; const a = seg[i], b = seg[i + 1];
  return [Math.round(a[0] + (b[0] - a[0]) * f), Math.round(a[1] + (b[1] - a[1]) * f), Math.round(a[2] + (b[2] - a[2]) * f)];
}

export function CloudViewer({ trace, pointSize, dark, density, reveal, colorMode, cameraMode, showCones = true, showTraj = true, surfel = false, showObb = false }:
  { trace: Trace; pointSize: number; dark: boolean; density: number; reveal: number; colorMode: ColorMode; cameraMode: CameraMode; showCones?: boolean; showTraj?: boolean; surfel?: boolean; showObb?: boolean }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const api = useRef<any>(null);
  const data = useRef<{ pts: Float32Array; offsets: number[]; nFrames: number } | null>(null);
  const caseRef = useRef(''); // to re-fit the camera only on a NEW case, not on density/color changes
  const orbitCam = useRef<{ p: THREE.Vector3; t: THREE.Vector3 } | null>(null); // remembered orbit view (preserved across configs/modes)
  const modeRef = useRef<CameraMode>(cameraMode); // stale-closure-safe mode for the controls listener
  modeRef.current = cameraMode;

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
    // whenever the user orbits, remember it so config/mode changes can restore this exact view (no camera yank)
    const onControls = () => { render(); if (modeRef.current === 'orbit') orbitCam.current = { p: camera.position.clone(), t: controls.target.clone() }; };
    controls.addEventListener('change', onControls);
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
        controls.removeEventListener('change', onControls); removeEventListener('resize', resize); ro.disconnect();
        document.removeEventListener('visibilitychange', onVis); renderer.dispose(); mount.removeChild(renderer.domElement);
      },
    };
    resize();
    return () => api.current?.dispose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { if (api.current) { api.current.scene.background = new THREE.Color(dark ? 0x0b1020 : 0xeef2f8); api.current.render(); } }, [dark]);
  useEffect(() => {
    if (!api.current) return;
    const m = api.current.cloud.material as THREE.PointsMaterial;
    m.size = surfel ? pointSize * 3.2 : pointSize;   // surfels: larger soft discs that merge into a surface
    m.map = surfel ? discTexture() : null;
    m.transparent = surfel; m.alphaTest = surfel ? 0.4 : 0;
    m.needsUpdate = true;
    api.current.render();
  }, [pointSize, surfel]);

  useEffect(() => {
    const a = api.current; if (!a || !trace) return;
    const pAll = b64ToF32(trace.points_b64), cAll = b64ToU8(trace.colors_b64);
    const nAll = (pAll.length / 3) | 0;
    const stride = Math.max(1, Math.round(density));
    const n = Math.ceil(nAll / stride);
    // world -> render frame via the shared transform (lib/coords), so all four renderers agree by construction.
    const pts = worldToRenderBuffer(pAll, stride);
    const cols = new Uint8Array(n * 3);
    for (let i = 0, j = 0; i < nAll; i += stride, j++) {
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
    a.frustums = []; const centers: THREE.Vector3[] = []; const fwds: THREE.Vector3[] = [];
    for (let i = 0; i < S; i++) {
      const p = poses.subarray(i * 12, i * 12 + 12);
      const c = poseCenter(p), fw = poseForward(p);                            // shared transform (lib/coords)
      centers.push(new THREE.Vector3(c[0], c[1], c[2]));
      fwds.push(new THREE.Vector3(fw[0], fw[1], fw[2]));
      const fg = new THREE.BufferGeometry().setFromPoints(fp.map((q) => {
        const r = poseApplyToRender(p, 0, q[0], q[1], q[2]);                   // pose then world->render, one path
        return new THREE.Vector3(r[0], r[1], r[2]);
      }));
      const ls = new THREE.LineSegments(fg, new THREE.LineBasicMaterial({ color: 0x33d6a6 })); ls.frustumCulled = false; a.traj.add(ls); a.frustums.push(ls);
    }
    const tg = new THREE.BufferGeometry().setFromPoints(centers);
    a.trajLine = new THREE.Line(tg, new THREE.LineBasicMaterial({ color: 0xff5252 })); a.trajLine.frustumCulled = false; a.traj.add(a.trajLine);
    a.centers = centers; a.fwds = fwds; a.bbox = g.boundingBox;

    // OBB diagnostic (shared coords): a box hugging the final cloud + an RGB axis triad at its min corner,
    // so the render frame is unambiguous and directly comparable across the four renderers. Toggle: showObb.
    if (a.obbGroup) { a.scene.remove(a.obbGroup); a.obbGroup = null; }
    {
      const obb = cloudObbRender(pAll, stride); const ax = obbAxes(obb);
      const grp = new THREE.Group();
      const boxPts: THREE.Vector3[] = [];
      for (const [i0, i1] of obb.edges) boxPts.push(new THREE.Vector3(...obb.corners[i0]), new THREE.Vector3(...obb.corners[i1]));
      const box = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(boxPts), new THREE.LineBasicMaterial({ color: 0x8899bb }));
      box.frustumCulled = false; grp.add(box);
      const axPts = [new THREE.Vector3(...ax.origin), new THREE.Vector3(...ax.x), new THREE.Vector3(...ax.origin), new THREE.Vector3(...ax.y), new THREE.Vector3(...ax.origin), new THREE.Vector3(...ax.z)];
      const axCol = new Float32Array([1, 0.2, 0.2, 1, 0.2, 0.2, 0.2, 1, 0.2, 0.2, 1, 0.2, 0.3, 0.55, 1, 0.3, 0.55, 1]); // +X red, +Y green, +Z blue
      const axGeo = new THREE.BufferGeometry().setFromPoints(axPts); axGeo.setAttribute('color', new THREE.BufferAttribute(axCol, 3));
      const axis = new THREE.LineSegments(axGeo, new THREE.LineBasicMaterial({ vertexColors: true })); axis.frustumCulled = false; grp.add(axis);
      grp.visible = showObb; a.scene.add(grp); a.obbGroup = grp;
    }

    const isNewCase = caseRef.current !== trace.case_id; // preserve the user's view on density/color changes
    caseRef.current = trace.case_id;
    if (isNewCase) { orbitCam.current = null; positionCamera(true); } // ONLY re-fit on a new case; never on config changes
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
      // TRUE sensor POV: the eye sits AT the camera center of the current frame and looks along the camera's
      // real forward axis (what the sensor saw), not a chase-cam behind it (Felipe 2026-07-05).
      const pos = a.centers[frame].clone(); const fwd = a.fwds[frame] || new THREE.Vector3(0, 0, 1);
      a.camera.position.copy(pos);
      a.controls.target.copy(pos.clone().addScaledVector(fwd, Math.max(r * 0.5, 0.5))); // look ahead along the heading
      a.controls.minDistance = 0.01; a.controls.maxDistance = r * 6;
    } else if (cameraMode === 'top') {
      a.controls.target.copy(c);
      // straight down the +Y axis with a tiny +Z tilt (not a diagonal one): keeps the view AXIS-ALIGNED
      // (X-right, Z-vertical) instead of a 45-degree "diamond", so it matches deck.gl's top exactly.
      a.camera.position.copy(c.clone().add(new THREE.Vector3(0, r * 2.4, r * 0.012)));
      a.controls.minDistance = r * 0.2; a.controls.maxDistance = r * 8;
    } else { // orbit
      a.controls.minDistance = r * 0.05; a.controls.maxDistance = r * 10;
      if (!fit && orbitCam.current) {                                 // restore the exact view the user had
        a.camera.position.copy(orbitCam.current.p); a.controls.target.copy(orbitCam.current.t);
      } else {                                                        // first fit for this case: frame it, then remember
        a.controls.target.copy(c);
        a.camera.position.copy(c.clone().add(new THREE.Vector3(0.5, 0.45, 1).normalize().multiplyScalar(r * 2.2)));
        orbitCam.current = { p: a.camera.position.clone(), t: a.controls.target.clone() };
      }
    }
    a.controls.update(); a.render();
  }
  // switching modes: recompute first/top, but RESTORE the remembered orbit view instead of re-fitting it
  useEffect(() => { positionCamera(false); /* eslint-disable-next-line */ }, [cameraMode]);

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
    if (a.trajLine) { a.trajLine.geometry.setDrawRange(0, Math.max(2, shownFrames)); a.trajLine.visible = showTraj; }
    if (a.frustums) a.frustums.forEach((f: THREE.LineSegments, i: number) => { f.visible = showCones && i < shownFrames; });
    if (cameraMode === 'first') positionCamera(false); // follow the player from the camera POV
    a.render();
  }
  useEffect(applyReveal, [reveal, showCones, showTraj]);
  useEffect(() => { const a = api.current; if (a?.obbGroup) { a.obbGroup.visible = showObb; a.render(); } }, [showObb]);

  return <div ref={mountRef} style={{ width: '100%', height: '100%', minHeight: 420 }} />;
}
