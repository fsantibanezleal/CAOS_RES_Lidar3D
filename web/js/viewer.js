// Three.js point-cloud + trajectory + camera-frustum viewer.
// Render-on-demand only (no idle rAF) so an unattended tab burns zero CPU.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const MAX_POINTS = 2_000_000;
const MAX_FRAMES = 400;

export class Viewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b1020);

    this.camera = new THREE.PerspectiveCamera(55, 1, 0.001, 5000);
    this.camera.position.set(0, -0.4, -3.2);
    this.camera.up.set(0, -1, 0); // these scenes are Y-down; flip so "up" looks natural

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = false;                 // no inertia -> no perpetual rAF
    this.controls.addEventListener('change', () => this.render());

    // point cloud (preallocated)
    const g = new THREE.BufferGeometry();
    this.posAttr = new THREE.BufferAttribute(new Float32Array(MAX_POINTS * 3), 3).setUsage(THREE.DynamicDrawUsage);
    this.colAttr = new THREE.BufferAttribute(new Uint8Array(MAX_POINTS * 3), 3, true).setUsage(THREE.DynamicDrawUsage);
    g.setAttribute('position', this.posAttr);
    g.setAttribute('color', this.colAttr);
    g.setDrawRange(0, 0);
    this.cloud = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.012, vertexColors: true, sizeAttenuation: true }));
    this.scene.add(this.cloud);
    this.nPts = 0;

    // trajectory line (preallocated)
    const tg = new THREE.BufferGeometry();
    this.trajAttr = new THREE.BufferAttribute(new Float32Array(MAX_FRAMES * 3), 3).setUsage(THREE.DynamicDrawUsage);
    tg.setAttribute('position', this.trajAttr);
    tg.setDrawRange(0, 0);
    this.traj = new THREE.Line(tg, new THREE.LineBasicMaterial({ color: 0xff5252, linewidth: 2 }));
    this.scene.add(this.traj);
    this.nFrames = 0;

    this.frustums = new THREE.Group();
    this.scene.add(this.frustums);

    this.grid = new THREE.GridHelper(20, 20, 0x274060, 0x18243c);
    this.grid.rotation.x = Math.PI / 2; // grid in XY (scenes are roughly XZ/ XY)
    this.scene.add(this.grid);
    this.scene.add(new THREE.AxesHelper(0.5));

    this._bounds = new THREE.Box3();
    this._resize();
    addEventListener('resize', () => this._resize());
    // pause/refresh on tab visibility (no compute while hidden)
    document.addEventListener('visibilitychange', () => { if (!document.hidden) this.render(); });
  }

  setPointSize(s) { this.cloud.material.size = s; this.render(); }
  setBackground(dark) { this.scene.background = new THREE.Color(dark ? 0x0b1020 : 0xf4f7fb); this.render(); }

  reset() {
    this.nPts = 0; this.nFrames = 0;
    this.cloud.geometry.setDrawRange(0, 0);
    this.traj.geometry.setDrawRange(0, 0);
    this.frustums.clear();
    this._bounds.makeEmpty();
    this.render();
  }

  addFrame({ points, colors, pose, isKeyframe }) {
    // points: Float32Array (3N), colors: Uint8Array (3N), pose: 12 floats (c2w row-major 3x4)
    const n = (points.length / 3) | 0;
    if (n > 0 && this.nPts + n <= MAX_POINTS) {
      this.posAttr.array.set(points, this.nPts * 3);
      this.colAttr.array.set(colors, this.nPts * 3);
      this.nPts += n;
      this.posAttr.needsUpdate = true; this.colAttr.needsUpdate = true;
      this.cloud.geometry.setDrawRange(0, this.nPts);
      // grow bounds cheaply with a decimated sample
      for (let i = 0; i < n; i += Math.max(1, (n / 64) | 0)) {
        this._bounds.expandByPoint(new THREE.Vector3(points[i*3], points[i*3+1], points[i*3+2]));
      }
    }
    // trajectory vertex from pose translation
    const cx = pose[3], cy = pose[7], cz = pose[11];
    if (this.nFrames < MAX_FRAMES) {
      this.trajAttr.array.set([cx, cy, cz], this.nFrames * 3);
      this.nFrames += 1;
      this.trajAttr.needsUpdate = true;
      this.traj.geometry.setDrawRange(0, this.nFrames);
      this.traj.geometry.computeBoundingSphere();
    }
    this._addFrustum(pose, isKeyframe);
    this.render();
  }

  _addFrustum(pose, isKeyframe) {
    const m = new THREE.Matrix4().set(
      pose[0], pose[1], pose[2], pose[3],
      pose[4], pose[5], pose[6], pose[7],
      pose[8], pose[9], pose[10], pose[11],
      0, 0, 0, 1);
    const s = 0.06, d = 0.10; // small frustum
    const pts = [
      [0,0,0],[ s, s, d],[0,0,0],[ s,-s, d],[0,0,0],[-s, s, d],[0,0,0],[-s,-s, d],
      [ s, s, d],[ s,-s, d],[ s,-s, d],[-s,-s, d],[-s,-s, d],[-s, s, d],[-s, s, d],[ s, s, d],
    ];
    const geo = new THREE.BufferGeometry().setFromPoints(pts.map(p => new THREE.Vector3(...p)));
    geo.applyMatrix4(m);
    const line = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({
      color: isKeyframe ? 0x33d6a6 : 0x4a6a9a }));
    this.frustums.add(line);
  }

  fitView() {
    if (this._bounds.isEmpty()) return;
    const c = this._bounds.getCenter(new THREE.Vector3());
    const r = Math.max(this._bounds.getSize(new THREE.Vector3()).length() * 0.6, 0.5);
    this.controls.target.copy(c);
    const dir = new THREE.Vector3(0.4, -0.5, -1).normalize();
    this.camera.position.copy(c.clone().add(dir.multiplyScalar(r * 2.2)));
    this.controls.update();
    this.render();
  }

  _resize() {
    const w = this.canvas.clientWidth || 800, h = this.canvas.clientHeight || 600;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    this.render();
  }

  render() { this.renderer.render(this.scene, this.camera); }
}
