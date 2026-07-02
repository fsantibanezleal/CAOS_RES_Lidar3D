// The third, genuinely-scalable renderer: Potree LOD. Loads a committed octree (metadata.json + octree.bin +
// hierarchy.bin, built offline by PotreeConverter under public/potree/<case>/) and renders it with true
// level-of-detail streaming via potree-core, so it scales to millions of points (only the visible/near nodes at
// the needed detail are drawn, bounded by a point budget). It needs a render loop for LOD; the loop pauses on a
// hidden tab (no idle CPU). The octree is baked in the render frame (Y-up), matching three.js/deck.gl.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Potree, PointColorType } from 'potree-core';
import { b64ToF32, type Trace } from '../lib/contract.types';
import type { CameraMode, ColorMode } from './CloudViewer';

// map our color toggle to a Potree material color source (RGB baked colors vs a height/elevation ramp).
// (Potree renders the FULL committed octree at LOD; per-frame replay is a three.js/deck.gl feature by design.)
const HEIGHT_TYPE = (PointColorType as any).ELEVATION ?? (PointColorType as any).HEIGHT ?? PointColorType.RGB;

export function PotreeViewer({ trace, pointSize, dark, density, cameraMode, colorMode }:
  { trace: Trace; pointSize: number; dark: boolean; density: number; cameraMode: CameraMode; colorMode: ColorMode }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const api = useRef<any>(null);
  const colorRef = useRef(colorMode); colorRef.current = colorMode; // current color for the async load

  useEffect(() => {
    const mount = mountRef.current!;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, 1, 0.01, 10000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    const grid = new THREE.GridHelper(20, 20, 0x274060, 0x18243c); scene.add(grid);
    const potree = new Potree();
    const resize = () => {
      const w = mount.clientWidth || 800, h = mount.clientHeight || 520;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    };
    resize(); addEventListener('resize', resize);
    const ro = new ResizeObserver(() => resize()); ro.observe(mount);
    const store: any = { scene, camera, controls, renderer, potree, pco: null };
    let raf = 0;
    const loop = () => {
      raf = requestAnimationFrame(loop);
      if (document.hidden) return;                       // pause LOD work on a hidden tab
      controls.update();
      if (store.pco) potree.updatePointClouds([store.pco], camera, renderer);
      renderer.setClearColor(dark ? 0x0b1020 : 0xeef2f8, 1);
      renderer.render(scene, camera);
    };
    api.current = store;
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf); removeEventListener('resize', resize); ro.disconnect();
      renderer.dispose(); mount.removeChild(renderer.domElement);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // load the case octree
  useEffect(() => {
    const a = api.current; if (!a || !trace) return;
    let cancelled = false;
    if (a.pco) { a.scene.remove(a.pco); a.pco = null; }
    const base = `${import.meta.env.BASE_URL}potree/${trace.case_id}/`;
    a.potree.loadPointCloud('metadata.json', base).then((pco: any) => {
      if (cancelled) { return; }
      pco.material.size = Math.max(0.5, pointSize * 45);
      pco.material.shape = 1;                             // circular points
      pco.material.pointColorType = colorRef.current === 'depth' ? HEIGHT_TYPE : PointColorType.RGB;   // baked RGB / height ramp
      try { (pco.material as any).inputColorEncoding = 1; (pco.material as any).outputColorEncoding = 1; } catch { /* older api */ }
      pco.material.needsUpdate = true;
      a.scene.add(pco); a.pco = pco;
      a.potree.pointBudget = Math.round(3_000_000 / Math.max(1, density));
      // fit orbit to the octree bounding box
      const bb: THREE.Box3 = pco.boundingBox ? pco.boundingBox.clone().applyMatrix4(pco.matrixWorld) : new THREE.Box3().setFromObject(pco);
      const c = bb.getCenter(new THREE.Vector3());
      const r = Math.max(bb.getSize(new THREE.Vector3()).length() * 0.5, 0.5);
      a.controls.target.copy(c);
      a.camera.position.copy(c.clone().add(new THREE.Vector3(0.5, 0.45, 1).normalize().multiplyScalar(r * 2.2)));
      a.controls.minDistance = r * 0.02; a.controls.maxDistance = r * 12;
      a.controls.update();
      // trajectory centers/forwards from the trace (same OpenCV->render transform as three.js/deck.gl), so Potree
      // supports first-person too (positions the camera along the reconstructed path).
      const poses = b64ToF32(trace.poses_b64); const S = (poses.length / 12) | 0;
      const centers: THREE.Vector3[] = [], fwds: THREE.Vector3[] = [];
      for (let i = 0; i < S; i++) {
        const p = poses.subarray(i * 12, i * 12 + 12);
        centers.push(new THREE.Vector3(p[3], -p[7], -p[11]));
        fwds.push(new THREE.Vector3(p[2], -p[6], -p[10]).normalize());
      }
      a.centers = centers; a.fwds = fwds; a.bbCenter = c; a.bbR = r;
      placeCamera();
    }).catch((e: unknown) => { console.error('potree load', e); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace]);

  useEffect(() => {
    const a = api.current; if (!a) return;
    a.potree.pointBudget = Math.round(3_000_000 / Math.max(1, density));
    if (a.pco) a.pco.material.size = Math.max(0.5, pointSize * 45);
  }, [pointSize, density]);

  // color toggle: baked RGB vs height ramp (responds to the same Color control as the other renderers)
  useEffect(() => {
    const a = api.current; if (!a || !a.pco) return;
    a.pco.material.pointColorType = colorMode === 'depth' ? HEIGHT_TYPE : PointColorType.RGB;
    a.pco.material.needsUpdate = true;
  }, [colorMode]);

  // orbit / top / FIRST-PERSON framing (first-person places the camera on the reconstructed trajectory, matching
  // three.js/surfels; the octree stays static, but the camera can now stand inside the map and look along the path)
  const placeCamera = () => {
    const a = api.current; if (!a || !a.pco || !a.bbCenter) return;
    const c: THREE.Vector3 = a.bbCenter, r: number = a.bbR;
    if (cameraMode === 'first' && a.centers?.length) {
      const pos: THREE.Vector3 = a.centers[a.centers.length - 1];
      const fwd: THREE.Vector3 = a.fwds[a.fwds.length - 1] || new THREE.Vector3(0, 0, 1);
      a.controls.target.copy(pos.clone().addScaledVector(fwd, Math.max(r * 0.3, 0.3)));   // look ahead along the path
      a.camera.position.copy(pos);
      a.controls.minDistance = 0.01; a.controls.maxDistance = r * 12;
    } else {
      a.controls.target.copy(c);
      const dir = cameraMode === 'top' ? new THREE.Vector3(0.001, 1, 0.001) : new THREE.Vector3(0.5, 0.45, 1);
      a.camera.position.copy(c.clone().add(dir.normalize().multiplyScalar(r * 2.2)));
      a.controls.minDistance = r * 0.02; a.controls.maxDistance = r * 12;
    }
    a.controls.update();
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(placeCamera, [cameraMode]);

  return <div ref={mountRef} style={{ width: '100%', height: '100%', minHeight: 420, background: dark ? '#0b1020' : '#eef2f8' }} />;
}
