// The 3D reconstruction viewer: decodes the baked artifact (CONTRACT 2) into a three.js RGB-colored point
// cloud + the camera-frustum trajectory, and replays it. Render-on-demand only (no idle rAF) so an
// unattended tab burns zero CPU (the "no compute bomb" rule); pauses on a hidden tab.
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { b64ToF32, b64ToU8, type Trace } from '../lib/contract.types';

export function CloudViewer({ trace, pointSize, dark }: { trace: Trace; pointSize: number; dark: boolean }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const api = useRef<{
    renderer: THREE.WebGLRenderer; scene: THREE.Scene; camera: THREE.PerspectiveCamera;
    controls: OrbitControls; cloud: THREE.Points; render: () => void; dispose: () => void;
  } | null>(null);

  // build scene once
  useEffect(() => {
    const mount = mountRef.current!;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, 1, 0.001, 5000);
    camera.up.set(0, -1, 0); // these scenes are Y-down
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = false;

    const cloud = new THREE.Points(
      new THREE.BufferGeometry(),
      new THREE.PointsMaterial({ size: pointSize, vertexColors: true, sizeAttenuation: true }),
    );
    scene.add(cloud);
    const traj = new THREE.Group();
    scene.add(traj);
    const grid = new THREE.GridHelper(20, 20, 0x274060, 0x18243c);
    grid.rotation.x = Math.PI / 2;
    scene.add(grid);

    const render = () => renderer.render(scene, camera);
    const resize = () => {
      const w = mount.clientWidth || 800, h = mount.clientHeight || 520;
      renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); render();
    };
    controls.addEventListener('change', render);
    addEventListener('resize', resize);
    const onVis = () => { if (!document.hidden) render(); };
    document.addEventListener('visibilitychange', onVis);

    (cloud as unknown as { _traj: THREE.Group })._traj = traj;
    api.current = {
      renderer, scene, camera, controls, cloud, render,
      dispose: () => {
        controls.removeEventListener('change', render); removeEventListener('resize', resize);
        document.removeEventListener('visibilitychange', onVis);
        renderer.dispose(); mount.removeChild(renderer.domElement);
      },
    };
    resize();
    return () => api.current?.dispose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // background by theme
  useEffect(() => {
    if (!api.current) return;
    api.current.scene.background = new THREE.Color(dark ? 0x0b1020 : 0xeef2f8);
    api.current.render();
  }, [dark]);

  // point size
  useEffect(() => {
    if (!api.current) return;
    (api.current.cloud.material as THREE.PointsMaterial).size = pointSize;
    api.current.render();
  }, [pointSize]);

  // load a trace -> rebuild the cloud + trajectory + frustums + fit view
  useEffect(() => {
    const a = api.current; if (!a || !trace) return;
    const pts = b64ToF32(trace.points_b64);
    const cols = b64ToU8(trace.colors_b64);
    const g = a.cloud.geometry;
    g.setAttribute('position', new THREE.BufferAttribute(pts, 3));
    g.setAttribute('color', new THREE.BufferAttribute(cols, 3, true));
    g.computeBoundingBox();

    const traj = (a.cloud as unknown as { _traj: THREE.Group })._traj;
    traj.clear();
    const poses = b64ToF32(trace.poses_b64); // [S*12]
    const S = poses.length / 12;
    const centers: number[] = [];
    for (let i = 0; i < S; i++) {
      const p = poses.subarray(i * 12, i * 12 + 12);
      const m = new THREE.Matrix4().set(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], 0, 0, 0, 1);
      centers.push(p[3], p[7], p[11]);
      const s = 0.05, d = 0.09;
      const fp = [[0, 0, 0], [s, s, d], [0, 0, 0], [s, -s, d], [0, 0, 0], [-s, s, d], [0, 0, 0], [-s, -s, d],
      [s, s, d], [s, -s, d], [s, -s, d], [-s, -s, d], [-s, -s, d], [-s, s, d], [-s, s, d], [s, s, d]];
      const fg = new THREE.BufferGeometry().setFromPoints(fp.map((q) => new THREE.Vector3(q[0], q[1], q[2])));
      fg.applyMatrix4(m);
      traj.add(new THREE.LineSegments(fg, new THREE.LineBasicMaterial({ color: 0x33d6a6 })));
    }
    const tg = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute(centers, 3));
    traj.add(new THREE.Line(tg, new THREE.LineBasicMaterial({ color: 0xff5252 })));

    // fit camera to the cloud
    const bb = g.boundingBox!;
    const c = bb.getCenter(new THREE.Vector3());
    const r = Math.max(bb.getSize(new THREE.Vector3()).length() * 0.55, 0.5);
    a.controls.target.copy(c);
    a.camera.position.copy(c.clone().add(new THREE.Vector3(0.4, -0.5, -1).normalize().multiplyScalar(r * 2.2)));
    a.controls.update();
    a.render();
  }, [trace]);

  return <div ref={mountRef} style={{ width: '100%', height: '100%', minHeight: 420 }} />;
}
