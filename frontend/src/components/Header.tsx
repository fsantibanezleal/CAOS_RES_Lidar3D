import { type Lang, t } from '../i18n';

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
        <div><h1>Lidar&nbsp;3D</h1><small>{t(lang, 'tagline')}</small></div>
      </div>
      <nav className="app">
        {PAGES.map(([id, key]) => (
          <button key={id} className={page === id ? 'on' : ''} onClick={() => setPage(id)}>{t(lang, key)}</button>
        ))}
      </nav>
      <div className="hspace" />
      <div className="hbtns">
        <a href="https://github.com/fsantibanezleal" target="_blank" rel="noreferrer" title="GitHub">⌥ GitHub</a>
        <a href="https://fsantibanezleal.github.io" target="_blank" rel="noreferrer" title="Personal site">◴ Site</a>
        <a href="https://fasl-work.com" target="_blank" rel="noreferrer" title="Portfolio">▣ Portfolio</a>
        <button onClick={openArch} title="How it works">ⓘ {t(lang, 'arch')}</button>
        <button onClick={() => setLang(lang === 'en' ? 'es' : 'en')}>{lang.toUpperCase()}</button>
        <button onClick={() => setDark(!dark)}>{dark ? '☾' : '☀'}</button>
      </div>
    </header>
  );
}
