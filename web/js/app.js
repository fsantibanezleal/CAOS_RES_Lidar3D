// App wiring: sources, live WebSocket stream, decode, viewer feed, i18n, theme, modal.
import { Viewer } from './viewer.js';

const $ = (id) => document.getElementById(id);
const I18N = {
  en: {
    tagline: 'Streaming 3D reconstruction workbench',
    source: 'Source', real: 'Real sequence', run: 'Run reconstruction', stop: 'Stop',
    frames: 'Max frames', decim: 'Point decimation', conf: 'Confidence keep', fit: 'Fit view',
    ptsize: 'Point size', live: 'Live frame + depth', stats: 'Live stats',
    f_frame: 'Frame', f_points: 'Points', f_fps: 'FPS', f_vram: 'GPU mem', f_path: 'Path length',
    arch: 'Architecture', archtitle: 'How it works', close: 'Close',
    note_real: 'Real sequences run on the actual lingbot-map model on the local GPU. No knobs change the data, only how it is processed and shown.',
    idle: 'Idle. Pick a source and run.', running: 'Reconstructing live on the GPU...',
    done: 'Done.', engine: 'Engine',
  },
  es: {
    tagline: 'Banco de reconstrucción 3D en streaming',
    source: 'Fuente', real: 'Secuencia real', run: 'Reconstruir', stop: 'Detener',
    frames: 'Cuadros máx.', decim: 'Diezmado de puntos', conf: 'Retención por confianza', fit: 'Encuadrar',
    ptsize: 'Tamaño de punto', live: 'Cuadro + profundidad', stats: 'Métricas en vivo',
    f_frame: 'Cuadro', f_points: 'Puntos', f_fps: 'FPS', f_vram: 'Mem GPU', f_path: 'Longitud trayecto',
    arch: 'Arquitectura', archtitle: 'Cómo funciona', close: 'Cerrar',
    note_real: 'Las secuencias reales corren sobre el modelo lingbot-map en la GPU local. Los controles no cambian el dato, solo cómo se procesa y muestra.',
    idle: 'Inactivo. Elige una fuente y ejecuta.', running: 'Reconstruyendo en vivo en la GPU...',
    done: 'Listo.', engine: 'Motor',
  },
};
let lang = localStorage.getItem('lidar3d_lang') || 'en';
let ws = null;
const viewer = new Viewer($('view'));

// ---- base64 -> typed arrays --------------------------------------------------------------
function b64Bytes(b64) {
  const bin = atob(b64), n = bin.length, out = new Uint8Array(n);
  for (let i = 0; i < n; i++) out[i] = bin.charCodeAt(i);
  return out;
}
const b64F32 = (b64) => new Float32Array(b64Bytes(b64).buffer);

// ---- i18n / theme ------------------------------------------------------------------------
function applyLang() {
  const t = I18N[lang];
  document.querySelectorAll('[data-t]').forEach(el => { el.textContent = t[el.dataset.t] ?? el.textContent; });
  $('langBtn').textContent = lang.toUpperCase();
}
function applyTheme() {
  const dark = localStorage.getItem('lidar3d_theme') !== 'light';
  document.body.classList.toggle('light', !dark);
  $('themeBtn').textContent = dark ? '☾' : '☀';
  viewer.setBackground(dark);
}

// ---- sources -----------------------------------------------------------------------------
async function loadSources() {
  const r = await fetch('/api/sources'); const { sources } = await r.json();
  const sel = $('source'); sel.innerHTML = '';
  for (const s of sources) {
    const o = document.createElement('option');
    o.value = s.id; o.textContent = `${s.label} (${s.n_frames})`;
    o.title = s.note; sel.appendChild(o);
  }
  const h = await (await fetch('/api/health')).json();
  $('gpu').textContent = h.gpu + (h.checkpoint_present ? '' : ' [checkpoint missing]');
}

// ---- run / stop --------------------------------------------------------------------------
function setStatus(key) { $('status').textContent = I18N[lang][key] ?? key; }

function run() {
  if (ws) ws.close();
  viewer.reset();
  let pathLen = 0, prev = null;
  const params = {
    max_frames: +$('frames').value, decimation: +$('decim').value,
    conf_quantile: +$('conf').value,
  };
  ws = new WebSocket(`ws://${location.host}/ws/stream`);
  ws.onopen = () => ws.send(JSON.stringify({ source_id: $('source').value, params }));
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.type === 'start') { $('progress').max = m.n_frames; $('engine').textContent = m.engine; setStatus('running'); }
    else if (m.type === 'frame') {
      viewer.addFrame({ points: b64F32(m.points_b64), colors: b64Bytes(m.colors_b64),
                        pose: m.pose_c2w, isKeyframe: m.is_keyframe });
      const c = [m.pose_c2w[3], m.pose_c2w[7], m.pose_c2w[11]];
      if (prev) pathLen += Math.hypot(c[0]-prev[0], c[1]-prev[1], c[2]-prev[2]);
      prev = c;
      $('progress').value = m.idx + 1;
      $('s_frame').textContent = `${m.idx + 1}/${m.total}`;
      $('s_points').textContent = viewer.nPts.toLocaleString();
      $('s_fps').textContent = m.fps.toFixed(1);
      $('s_vram').textContent = m.vram_gb.toFixed(1) + ' GB';
      $('s_path').textContent = pathLen.toFixed(2) + ' m';
      if (m.depth_png) $('depth').src = m.depth_png;
      if (m.idx === 7) viewer.fitView();   // fit once the scale block has landed
    }
    else if (m.type === 'done') { setStatus('done'); ws = null; }
    else if (m.type === 'error') { setStatus(m.message); ws = null; }
  };
  ws.onclose = () => { ws = null; };
}
function stop() { if (ws) { ws.close(); ws = null; } setStatus('done'); }

// ---- wire up -----------------------------------------------------------------------------
$('runBtn').onclick = run;
$('stopBtn').onclick = stop;
$('fitBtn').onclick = () => viewer.fitView();
$('ptsize').oninput = (e) => viewer.setPointSize(+e.target.value);
$('langBtn').onclick = () => { lang = lang === 'en' ? 'es' : 'en'; localStorage.setItem('lidar3d_lang', lang); applyLang(); setStatus(ws ? 'running' : 'idle'); };
$('themeBtn').onclick = () => { localStorage.setItem('lidar3d_theme', localStorage.getItem('lidar3d_theme') === 'light' ? 'dark' : 'light'); applyTheme(); };
$('archBtn').onclick = () => $('archModal').classList.add('open');
$('archClose').onclick = () => $('archModal').classList.remove('open');
$('archModal').onclick = (e) => { if (e.target === $('archModal')) $('archModal').classList.remove('open'); };

applyTheme(); applyLang(); setStatus('idle'); loadSources();
