import type { Lang } from '../i18n';
import { APP_VERSION } from '../version';

export function Footer({ lang }: { lang: Lang }) {
  const en = lang === 'en';
  return (
    <footer className="app">
      <span>Lidar&nbsp;3D · CAOS research lab</span>
      <span className="ver">v{APP_VERSION}</span>
      <span>·</span>
      <span>{en ? 'Engines' : 'Motores'}: {en ? 'Estela (our depth+pose net)' : 'Estela (nuestra red profundidad+pose)'} · {en ? 'Open3D ICP' : 'Open3D ICP'} · <a href="https://github.com/Robbyant/lingbot-map" target="_blank" rel="noreferrer">lingbot-map</a> {en ? 'SOTA ref' : 'ref SOTA'} (Apache-2.0)</span>
      <span>·</span>
      <a href="https://github.com/fsantibanezleal/CAOS_RES_Lidar3D" target="_blank" rel="noreferrer">GitHub</a>
      <span>·</span>
      <span>{en
        ? 'Replay of committed artifacts; live reconstruction runs on a local GPU.'
        : 'Replay de artefactos commiteados; la reconstrucción en vivo corre en GPU local.'}</span>
    </footer>
  );
}
