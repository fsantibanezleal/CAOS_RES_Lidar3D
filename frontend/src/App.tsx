// The 6-page shell (ADR-0016): header (brand + nav + icons + lang + theme + arch modal) · the page ·
// footer. Page state + theme/lang in localStorage. The App page is the workbench; the rest are deep texts.
import { useEffect, useState } from 'react';
import './style.css';
import { ArchModal } from './components/ArchModal';
import { Footer } from './components/Footer';
import { Header, type Page } from './components/Header';
import { type Lang } from './i18n';
import { AppPage } from './pages/AppPage';
import { Benchmark } from './pages/Benchmark';
import { Experiments } from './pages/Experiments';
import { Implementation } from './pages/Implementation';
import { Introduction } from './pages/Introduction';
import { Methodology } from './pages/Methodology';

export default function App() {
  const [page, setPage] = useState<Page>('app');
  const [lang, setLang] = useState<Lang>((localStorage.getItem('l3d_lang') as Lang) || 'en');
  const [dark, setDark] = useState(localStorage.getItem('l3d_theme') !== 'light');
  const [arch, setArch] = useState(false);

  useEffect(() => {
    document.body.classList.toggle('light', !dark);
    localStorage.setItem('l3d_theme', dark ? 'dark' : 'light');
  }, [dark]);
  useEffect(() => { localStorage.setItem('l3d_lang', lang); }, [lang]);

  return (
    <>
      <Header page={page} setPage={setPage} lang={lang} setLang={setLang}
        dark={dark} setDark={setDark} openArch={() => setArch(true)} />
      <main className="app">
        {page === 'app' && <AppPage lang={lang} dark={dark} />}
        {page === 'intro' && <Introduction lang={lang} />}
        {page === 'method' && <Methodology lang={lang} />}
        {page === 'impl' && <Implementation lang={lang} />}
        {page === 'exp' && <Experiments lang={lang} />}
        {page === 'bench' && <Benchmark lang={lang} />}
      </main>
      <Footer lang={lang} />
      {arch && <ArchModal lang={lang} onClose={() => setArch(false)} />}
    </>
  );
}
