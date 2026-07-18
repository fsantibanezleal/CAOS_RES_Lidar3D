import { useEffect, useState, type JSX } from 'react';
import { type Lang } from '../i18n';
import { DataContractsDiagram, DesignFlowDiagram, GCTDiagram, LanesDiagram, WebAppFlowDiagram } from './Diagrams';

// ADR-0058: the in-app "how it works" modal, a tab strip of themed SVGs (>= 5 tabs: the app + design flow /
// lanes web-offline-compute / web-app flow / the science / data contracts), Esc-to-close, role="dialog".
export function ArchModal({ lang, onClose }: { lang: Lang; onClose: () => void }) {
  const en = lang === 'en';
  const [tab, setTab] = useState(0);
  useEffect(() => {
    const on = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', on);
    return () => document.removeEventListener('keydown', on);
  }, [onClose]);

  const tabs: { label: string; diagram: JSX.Element; body: string }[] = [
    { label: en ? 'The app' : 'La app', diagram: <DesignFlowDiagram lang={lang} />,
      body: en ? 'Lidar 3D turns a video or LiDAR stream into camera poses, dense metric depth, and a colored world point cloud. The diagram shows both what it is and how it was designed and built: research, implement, train and validate, bake a committed artifact, build the SPA, deploy. The App shown here replays a committed artifact; it does not recompute in the browser.'
                : 'Lidar 3D convierte un stream de video o LiDAR en poses de cámara, profundidad métrica densa y una nube de puntos de mundo coloreada. El diagrama muestra qué es y cómo se diseñó y construyó: research, implementar, entrenar y validar, precalcular un artefacto confirmado, construir la SPA, desplegar. La App reproduce un artefacto confirmado; no recomputa en el browser.' },
    { label: en ? 'Lanes' : 'Carriles', diagram: <LanesDiagram lang={lang} />,
      body: en ? 'Three lanes (ADR-0057). offline (precompute, GPU): the engine bakes a committed artifact. replay (this static web): loads only committed artifacts and replays them. live (local-GPU API, dormant): real-time reconstruction of custom footage on a machine with the GPU. The split of what runs in the web vs offline vs compute is explicit.'
                : 'Tres carriles (ADR-0057). offline (precómputo, GPU): el motor precalcula un artefacto confirmado. replay (esta web estática): carga solo artefactos confirmados y los reproduce. live (API GPU local, latente): reconstrucción en vivo de video propio en una máquina con GPU. La separación web vs offline vs cómputo es explícita.' },
    { label: en ? 'Web-app flow' : 'Flujo web', diagram: <WebAppFlowDiagram lang={lang} />,
      body: en ? 'The SPA: committed artifacts are overlaid into public/ by copy-data, fetched and decoded into typed arrays, and rendered by the selectable renderer (three.js or deck.gl) with the trajectory and the camera modes. The TypeScript contract types mirror the artifact, so a drift fails the build. Six pages (ADR-0016): the App plus five deep tabbed texts plus this modal.'
                : 'La SPA: los artefactos confirmados se superponen a public/ con copy-data, se descargan y decodifican a typed arrays, y los renderiza el motor seleccionable (three.js o deck.gl) con la trayectoria y los modos de cámara. Los tipos TypeScript reflejan el artefacto, así un drift rompe el build. Seis páginas (ADR-0016): la App más cinco textos tabulados profundos más este modal.' },
    { label: en ? 'The science' : 'La ciencia', diagram: <GCTDiagram lang={lang} />,
      body: en ? 'The camera engine is a Geometric Context Transformer: a frozen DINOv2 ViT tokenizes each frame; 24 blocks alternate frame and cross-frame attention over a bounded three-tier context (anchor, pose window, trajectory memory) held in a paged KV cache; heads emit pose, dense metric depth, and confidence; our geometry unprojects depth to the world cloud. The lab also runs Estela, our own from-scratch depth+pose model, trained on TUM RGB-D.'
                : 'El motor de cámara es un Geometric Context Transformer: un DINOv2 ViT congelado tokeniza cada cuadro; 24 bloques alternan atención por-cuadro y entre-cuadros sobre un contexto acotado de tres niveles (ancla, ventana de pose, memoria de trayectoria) en un KV cache paginado; las cabezas emiten pose, profundidad métrica densa y confianza; nuestra geometría desproyecta a la nube de mundo. El lab también ejecuta Estela, nuestro modelo de profundidad+pose desde cero, entrenado en TUM RGB-D.' },
    { label: en ? 'Data contracts' : 'Contratos', diagram: <DataContractsDiagram lang={lang} />,
      body: en ? 'Two enforced contracts. CONTRACT 1 (ingestion): a bring-your-own-data gate that accepts a sequence only if it satisfies the schema and an explicit outlier policy; bad inputs are rejected with a reason, never coerced. CONTRACT 2 (artifact): every run writes a compact trace + a manifest (params, seed, lane/gate verdict, bytes); the TypeScript types mirror it so a drift fails the build. No absolute path is ever written.'
                : 'Dos contratos aplicados. CONTRATO 1 (ingesta): una puerta de datos propios que acepta una secuencia solo si cumple el esquema y una política de outliers explícita; entradas malas se rechazan con razón, nunca se coaccionan. CONTRATO 2 (artefacto): cada corrida escribe un trace compacto + un manifest (params, seed, veredicto lane/gate, bytes); los tipos TypeScript lo reflejan, así un drift rompe el build. Nunca se escribe una ruta absoluta.' },
  ];

  return (
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="card" role="dialog" aria-modal="true" aria-label={en ? 'How it works' : 'Cómo funciona'}>
        <div className="card-h">
          <b>{en ? 'How it works' : 'Cómo funciona'}</b>
          <button className="primary" onClick={onClose}>{en ? 'Close' : 'Cerrar'}</button>
        </div>
        <div className="card-b">
          <div className="subtabs" role="tablist">
            {tabs.map((t, i) => (
              <button key={i} role="tab" aria-selected={i === tab} className={'stab' + (i === tab ? ' on' : '')} onClick={() => setTab(i)}>{t.label}</button>
            ))}
          </div>
          {tabs[tab].diagram}
          <p>{tabs[tab].body}</p>
        </div>
      </div>
    </div>
  );
}
