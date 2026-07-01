import { type Lang, t } from '../i18n';
import { APP_VERSION } from '../version';
import { GitHubIcon, GlobeIcon, GridIcon, InfoIcon, MoonIcon, SunIcon } from './Icons';

export type Page = 'app' | 'intro' | 'method' | 'impl' | 'exp' | 'bench';
const PAGES: [Page, string][] = [
  ['app', 'nav_app'], ['intro', 'nav_intro'], ['method', 'nav_method'],
  ['impl', 'nav_impl'], ['exp', 'nav_exp'], ['bench', 'nav_bench'],
];

export function Header(props: {
  page: Page; setPage: (p: Page) => void; lang: Lang; setLang: (l: Lang) => void;
  dark: boolean; setDark: (d: boolean) => void; openArch: () => void;
}) {
  const { page, setPage, lang, setLang, dark, setDark, openArch } = props;
  return (
    <header className="app">
      <div className="brand">
        <span className="logo">◇</span>
        <div>
          <h1>Lidar&nbsp;3D <span className="ver">v{APP_VERSION}</span></h1>
          <small>{t(lang, 'tagline')}</small>
        </div>
      </div>
      <nav className="app">
        {PAGES.map(([id, key]) => (
          <button key={id} className={page === id ? 'on' : ''} onClick={() => setPage(id)}>{t(lang, key)}</button>
        ))}
      </nav>
      <div className="hspace" />
      <div className="hbtns">
        <a href="https://github.com/fsantibanezleal/CAOS_RES_Lidar3D" target="_blank" rel="noreferrer" title="GitHub repository" aria-label="GitHub"><GitHubIcon /></a>
        <a href="https://fsantibanezleal.github.io" target="_blank" rel="noreferrer" title="Personal site" aria-label="Personal site"><GlobeIcon /></a>
        <a href="https://fasl-work.com" target="_blank" rel="noreferrer" title="Portfolio" aria-label="Portfolio"><GridIcon /></a>
        <button onClick={openArch} title={t(lang, 'arch')} aria-label={t(lang, 'arch')} className="ic-txt"><InfoIcon /><span>{t(lang, 'arch')}</span></button>
        <button onClick={() => setLang(lang === 'en' ? 'es' : 'en')} title="Language" aria-label="Language">{lang.toUpperCase()}</button>
        <button onClick={() => setDark(!dark)} title={dark ? 'Light theme' : 'Dark theme'} aria-label="Theme">{dark ? <SunIcon /> : <MoonIcon />}</button>
      </div>
    </header>
  );
}
