import katex from 'katex';
import 'katex/dist/katex.min.css';

export function Katex({ tex, block }: { tex: string; block?: boolean }) {
  const html = katex.renderToString(tex, { displayMode: !!block, throwOnError: false });
  return <span className={block ? 'katex-block' : ''} dangerouslySetInnerHTML={{ __html: html }} />;
}
