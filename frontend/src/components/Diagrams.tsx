// High-quality, theme-aware SVG diagrams (ADR-0058). Reused by the architecture modal and the content pages.
// Colors come from the CSS theme variables so they track light/dark. No raster images, no ASCII.
import type { JSX } from 'react';
import type { Lang } from '../i18n';

const C = {
  box: 'var(--panel)', bg: 'var(--bg2)', line: 'var(--line)', acc: 'var(--acc)', acc2: 'var(--acc2)',
  warn: 'var(--warn)', txt: 'var(--txt)', mut: 'var(--mut)',
};

function Defs() {
  return (
    <defs>
      <marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill={C.mut} />
      </marker>
      <marker id="ahA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0 0 L10 5 L0 10 z" fill={C.acc} />
      </marker>
    </defs>
  );
}

function Box({ x, y, w, h, title, sub, accent, dashed }: {
  x: number; y: number; w: number; h: number; title: string; sub?: string; accent?: string; dashed?: boolean;
}) {
  const stroke = accent ?? C.line;
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="8" fill={C.box} stroke={stroke} strokeWidth={accent ? 1.6 : 1.1}
        strokeDasharray={dashed ? '5 4' : undefined} />
      <text x={x + w / 2} y={y + (sub ? h / 2 - 4 : h / 2 + 4)} textAnchor="middle" fontSize="12.5" fontWeight="600" fill={C.txt}>{title}</text>
      {sub && <text x={x + w / 2} y={y + h / 2 + 12} textAnchor="middle" fontSize="10.5" fill={C.mut}>{sub}</text>}
    </g>
  );
}
const Arrow = ({ x1, y1, x2, y2, accent, dashed }: { x1: number; y1: number; x2: number; y2: number; accent?: boolean; dashed?: boolean }) => (
  <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={accent ? C.acc : C.mut} strokeWidth="1.5"
    strokeDasharray={dashed ? '5 4' : undefined} markerEnd={`url(#${accent ? 'ahA' : 'ah'})`} />
);
const Lane = ({ x, y, w, h, label, color }: { x: number; y: number; w: number; h: number; label: string; color: string }) => (
  <g>
    <rect x={x} y={y} width={w} height={h} rx="12" fill="none" stroke={color} strokeWidth="1" opacity="0.5" strokeDasharray="2 3" />
    <text x={x + 12} y={y + 18} fontSize="11.5" fontWeight="700" fill={color} letterSpacing="0.4">{label}</text>
  </g>
);
const Frame = ({ children, h = 380, vb = '0 0 720 380' }: { children: JSX.Element; h?: number; vb?: string }) => (
  <div className="svgwrap"><svg viewBox={vb} width="100%" height={h} role="img" preserveAspectRatio="xMidYMid meet">{children}</svg></div>
);

// ---- 1) The three lanes (ADR-0057) + the data flow --------------------------------------------------------
export function LanesDiagram({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <Frame h={360} vb="0 0 720 360">
      <><Defs />
        <Lane x={8} y={26} w={250} h={320} label={en ? 'OFFLINE · precompute · GPU' : 'OFFLINE · precómputo · GPU'} color={C.acc} />
        <Lane x={270} y={26} w={210} h={320} label={en ? 'REPLAY · this web · static' : 'REPLAY · esta web · estática'} color={C.acc2} />
        <Lane x={492} y={26} w={220} h={320} label={en ? 'LIVE · local-GPU API · dormant' : 'LIVE · API GPU local · latente'} color={C.mut} />

        <Box x={40} y={48} w={186} h={40} title={en ? 'RGB / LiDAR sequence' : 'Secuencia RGB / LiDAR'} sub="CONTRACT 1" />
        <Arrow x1={133} y1={88} x2={133} y2={104} accent />
        <Box x={40} y={106} w={186} h={40} title="preprocess" sub={en ? 'decode · resize · scale' : 'decodif · resize · escala'} />
        <Arrow x1={133} y1={146} x2={133} y2={162} accent />
        <Box x={40} y={164} w={186} h={44} title="infer · lingbot GCT" sub={en ? 'poses + metric depth' : 'poses + prof. métrica'} accent={C.acc} />
        <Arrow x1={133} y1={208} x2={133} y2={224} accent />
        <Box x={40} y={226} w={186} h={40} title="refine · Open3D" sub={en ? 'voxel · outliers · color' : 'voxel · outliers · color'} />
        <Arrow x1={133} y1={266} x2={133} y2={282} accent />
        <Box x={40} y={284} w={186} h={44} title="evaluate · export" sub="ATE / RPE · trace.json" accent={C.acc} />

        <Box x={286} y={150} w={178} h={64} title={en ? 'committed artifact' : 'artefacto confirmado'} sub="trace.json + manifest (CONTRACT 2)" accent={C.acc2} />
        <Box x={286} y={244} w={178} h={64} title={en ? 'three.js replay' : 'replay three.js'} sub={en ? 'point cloud + trajectory' : 'nube + trayectoria'} accent={C.acc2} />
        <Arrow x1={286} y1={306} x2={236} y2={306} />{/* from export to replay */}
        <path d={`M226 306 H270 V182 H286`} fill="none" stroke={C.acc} strokeWidth="1.5" markerEnd="url(#ahA)" />
        <Arrow x1={375} y1={214} x2={375} y2={244} accent />

        <Box x={508} y={150} w={188} h={44} title={en ? 'custom footage' : 'video propio'} sub={en ? 'browser upload' : 'subida en browser'} dashed accent={C.mut} />
        <Arrow x1={602} y1={194} x2={602} y2={210} dashed />
        <Box x={508} y={212} w={188} h={52} title="FastAPI + GPU" sub={en ? '4.6 GB checkpoint · 1B ViT' : 'checkpoint 4.6 GB · ViT 1B'} dashed accent={C.mut} />
        <Arrow x1={602} y1={264} x2={602} y2={280} dashed />
        <Box x={508} y={282} w={188} h={44} title="WebSocket stream" sub={en ? 'real-time reconstruction' : 'reconstrucción en vivo'} dashed accent={C.mut} />
        <text x={602} y={132} textAnchor="middle" fontSize="10" fill={C.mut}>{en ? '(too heavy for the browser)' : '(demasiado pesado para el browser)'}</text>
      </>
    </Frame>
  );
}

// ---- 2) The Geometric Context Transformer (the network) ---------------------------------------------------
export function GCTDiagram({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <Frame h={320} vb="0 0 720 320">
      <><Defs />
        <Box x={16} y={128} w={104} h={64} title={en ? 'frame t' : 'cuadro t'} sub={en ? 'RGB image' : 'imagen RGB'} />
        <Arrow x1={120} y1={160} x2={140} y2={160} />
        <Box x={140} y={120} w={118} h={80} title="DINOv2 ViT" sub={en ? 'frozen · patch-14' : 'congelado · patch-14'} accent={C.acc2} />
        <Arrow x1={258} y1={160} x2={278} y2={160} />
        <Box x={278} y={104} w={150} h={112} title={en ? '24 blocks' : '24 bloques'} sub={en ? 'frame ⇄ cross-frame attn' : 'atención cuadro ⇄ entre-cuadros'} accent={C.acc} />
        <Box x={296} y={150} w={114} h={22} title={en ? 'Geometric Context' : 'Contexto Geométrico'} />
        <Arrow x1={428} y1={160} x2={448} y2={160} accent />

        <Box x={448} y={92} w={132} h={38} title={en ? 'pose head' : 'cabeza de pose'} sub="absT·quatR·FoV" accent={C.acc} />
        <Box x={448} y={140} w={132} h={38} title={en ? 'depth head' : 'cabeza de prof.'} sub={en ? 'dense metric' : 'métrica densa'} accent={C.acc} />
        <Box x={448} y={188} w={132} h={38} title={en ? 'conf. head' : 'cabeza conf.'} sub="σ(u,v)" />
        <Arrow x1={580} y1={159} x2={600} y2={159} accent />
        <Box x={600} y={120} w={104} h={80} title={en ? 'unproject' : 'desproyectar'} sub={en ? 'world cloud' : 'nube mundo'} accent={C.acc} />

        <text x={353} y={250} textAnchor="middle" fontSize="11" fontWeight="600" fill={C.mut}>{en ? 'paged KV cache (anchor · window · trajectory memory)' : 'KV cache paginado (ancla · ventana · memoria de trayectoria)'}</text>
        <path d="M353 236 V226" stroke={C.mut} strokeWidth="1.2" markerEnd="url(#ah)" />
        <rect x={150} y={258} width={406} height={30} rx="6" fill={C.bg} stroke={C.line} />
        <text x={353} y={277} textAnchor="middle" fontSize="10.5" fill={C.mut}>{en ? 'causal stream · constant tokens/frame · ~20 FPS' : 'stream causal · tokens/cuadro constantes · ~20 FPS'}</text>
      </>
    </Frame>
  );
}

// ---- The app + the design/build lifecycle -----------------------------------------------------------------
export function DesignFlowDiagram({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  const steps: [string, string][] = [
    [en ? 'research / fiche' : 'research / ficha', 'wip/lidar3d + surveys'],
    [en ? 'implement' : 'implementar', 'data-pipeline/lidar3dlab'],
    [en ? 'train + validate' : 'entrenar + validar', 'train/ · geom test · ATE'],
    [en ? 'bake artifact' : 'precalcular artefacto', 'stages/export · trace.json'],
    [en ? 'build SPA' : 'build SPA', 'frontend/ · copy-data'],
    [en ? 'deploy' : 'desplegar', 'Pages · fasl-work.com'],
  ];
  return (
    <Frame h={230} vb="0 0 720 230">
      <><Defs />
        <text x={16} y={22} fontSize="12.5" fontWeight="700" fill={C.txt}>{en ? 'Lidar 3D: what it is + how it was designed and built' : 'Lidar 3D: qué es + cómo se diseñó y construyó'}</text>
        <Box x={16} y={40} w={688} h={40} title={en ? 'A streaming 3D reconstruction lab: video/LiDAR to poses + metric depth + a colored world cloud' : 'Un lab de reconstrucción 3D en streaming: video/LiDAR a poses + profundidad métrica + nube de mundo coloreada'} accent={C.acc2} />
        {steps.map(([t, s], i) => {
          const x = 16 + i * 116;
          return <g key={i}><Box x={x} y={110} w={104} h={54} title={t} sub={s} accent={i === 2 ? C.acc : undefined} />
            {i < steps.length - 1 && <Arrow x1={x + 104} y1={137} x2={x + 116} y2={137} accent />}</g>;
        })}
        <text x={360} y={196} textAnchor="middle" fontSize="10.5" fill={C.mut}>{en ? 'the design-build flow (research to deploy); the App shown is the replay of a committed artifact' : 'el flujo de diseño-construcción (research a deploy); la App mostrada es el replay de un artefacto confirmado'}</text>
      </>
    </Frame>
  );
}

// ---- The web-app (SPA) flow --------------------------------------------------------------------------------
export function WebAppFlowDiagram({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <Frame h={280} vb="0 0 720 280">
      <><Defs />
        <Box x={16} y={40} w={150} h={54} title="committed artifacts" sub="data/derived/*/trace.json" accent={C.acc} />
        <Arrow x1={166} y1={67} x2={186} y2={67} accent />
        <Box x={186} y={40} w={140} h={54} title="copy-data.mjs" sub={en ? 'overlay -> public/data' : 'overlay -> public/data'} />
        <Arrow x1={326} y1={67} x2={346} y2={67} />
        <Box x={346} y={40} w={150} h={54} title="api/artifacts.ts" sub="fetch + b64 -> typed arrays" accent={C.acc2} />
        <Arrow x1={496} y1={67} x2={516} y2={67} />
        <Box x={516} y={40} w={188} h={54} title="contract.types.ts" sub={en ? 'MIRROR (drift fails tsc build)' : 'ESPEJO (un drift rompe tsc)'} accent={C.warn} />

        <Box x={16} y={140} w={210} h={60} title="AppPage (workbench)" sub={en ? 'case selector + replay + controls' : 'selector de caso + replay + controles'} accent={C.acc2} />
        <Arrow x1={226} y1={170} x2={246} y2={170} />
        <Box x={246} y={140} w={230} h={60} title={en ? 'renderer: three.js | deck.gl' : 'renderer: three.js | deck.gl'} sub={en ? 'point cloud + trajectory + camera modes' : 'nube + trayectoria + modos de cámara'} accent={C.acc} />
        <Arrow x1={476} y1={170} x2={496} y2={170} />
        <Box x={496} y={140} w={208} h={60} title={en ? '6 pages (ADR-0016)' : '6 páginas (ADR-0016)'} sub={en ? 'App + 5 deep tabbed texts + ⓘ modal' : 'App + 5 textos tabulados + modal ⓘ'} />
        <path d="M120 94 V140" stroke={C.acc} strokeWidth="1.5" markerEnd="url(#ahA)" />
        <text x={360} y={238} textAnchor="middle" fontSize="10.5" fill={C.mut}>{en ? 'static SPA: it only replays committed artifacts, it never recomputes in the browser' : 'SPA estática: solo reproduce artefactos confirmados, nunca recomputa en el browser'}</text>
      </>
    </Frame>
  );
}

// ---- The two data contracts + the design ------------------------------------------------------------------
export function DataContractsDiagram({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <Frame h={280} vb="0 0 720 280">
      <><Defs />
        <Lane x={8} y={26} w={340} h={230} label={en ? 'CONTRACT 1 · ingestion (bring-your-own-data)' : 'CONTRATO 1 · ingesta (datos propios)'} color={C.acc2} />
        <Lane x={360} y={26} w={352} h={230} label={en ? 'CONTRACT 2 · artifact (pipeline to web)' : 'CONTRATO 2 · artefacto (pipeline a web)'} color={C.acc} />
        <Box x={28} y={54} w={300} h={40} title={en ? 'RGB / LiDAR sequence + knobs' : 'Secuencia RGB / LiDAR + knobs'} sub="io/schema.py SequenceSpec" />
        <Arrow x1={178} y1={94} x2={178} y2={110} />
        <Box x={28} y={112} w={300} h={44} title="validate_rows (io/contract.py)" sub={en ? 'accept · reject-with-reason · flag' : 'aceptar · rechazar-con-razón · marcar'} accent={C.acc2} />
        <Arrow x1={178} y1={156} x2={178} y2={172} />
        <Box x={28} y={174} w={300} h={44} title={en ? 'outlier policy (explicit)' : 'política de outliers (explícita)'} sub={en ? 'never silently coerced' : 'nunca coaccionado en silencio'} />

        <Box x={380} y={54} w={312} h={44} title="trace.json (core/trace.py)" sub={en ? 'b64 cloud + poses + depth/RGB thumbs' : 'nube b64 + poses + thumbs depth/RGB'} accent={C.acc} />
        <Arrow x1={536} y1={98} x2={536} y2={114} accent />
        <Box x={380} y={116} w={312} h={44} title="manifest.json (core/manifest.py)" sub={en ? 'params · seed · lane/gate verdict · bytes' : 'params · seed · veredicto lane/gate · bytes'} accent={C.acc} />
        <Arrow x1={536} y1={160} x2={536} y2={176} accent />
        <Box x={380} y={178} w={312} h={44} title="contract.types.ts" sub={en ? 'TypeScript MIRROR: a drift fails the build' : 'ESPEJO TypeScript: un drift rompe el build'} accent={C.warn} />
        <path d={`M328 134 H360`} stroke={C.mut} strokeWidth="1.5" markerEnd="url(#ah)" />
      </>
    </Frame>
  );
}

// ---- 3) The three-tier attention context ------------------------------------------------------------------
export function ContextDiagram({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  const cell = (i: number, fill: string, stroke: string) => <rect key={i} x={40 + i * 26} y={0} width={20} height={28} rx="3" fill={fill} stroke={stroke} strokeWidth="1" />;
  return (
    <Frame h={260} vb="0 0 720 260">
      <><Defs />
        <text x={20} y={22} fontSize="12" fontWeight="700" fill={C.txt}>{en ? 'Per-frame context = a constant + a tiny linear part' : 'Contexto por cuadro = una constante + una parte lineal diminuta'}</text>
        <g transform="translate(0 44)">
          {[0, 1, 2].map((i) => cell(i, C.acc2, C.acc2))}
          <text x={40} y={-6} fontSize="10.5" fill={C.acc2}>{en ? 'anchor · n frames · full tokens + metric scale' : 'ancla · n cuadros · tokens completos + escala'}</text>
        </g>
        <g transform="translate(0 104)">
          {[0, 1, 2, 3, 4, 5].map((i) => cell(i, C.acc, C.acc))}
          <text x={40} y={-6} fontSize="10.5" fill={C.acc}>{en ? 'pose window · k≈16–64 recent · full resolution' : 'ventana de pose · k≈16–64 recientes · resolución completa'}</text>
        </g>
        <g transform="translate(0 164)">
          {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((i) => <rect key={i} x={40 + i * 26} y={0} width={20} height={12} rx="2" fill={C.bg} stroke={C.mut} strokeWidth="1" />)}
          <text x={40} y={-6} fontSize="10.5" fill={C.mut}>{en ? 'trajectory memory · all older frames · 6 tokens each (Video-RoPE)' : 'memoria de trayectoria · cuadros viejos · 6 tokens c/u (Video-RoPE)'}</text>
        </g>
        <text x={360} y={230} textAnchor="middle" fontSize="11" fill={C.mut}>{en ? '(n+k)·M + 6T tokens vs M·T naive: ≈80× fewer over 10k frames' : '(n+k)·M + 6T tokens vs M·T naive: ≈80× menos sobre 10k cuadros'}</text>
      </>
    </Frame>
  );
}
