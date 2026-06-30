// Prebuild: copy the committed CONTRACT-2 artifacts (../data/derived) into the SPA's public/ so the static site
// replays them, and inline the lidar3dlab sources for the live (Pyodide) lane. Canonical copies live in ../data
// and ../data-pipeline — public/ is a build-time overlay (git-ignored).
import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const PUB = join(HERE, 'public');

// 1) data/derived -> public/data (traces under <case>/trace.json + manifests/ subdir incl. index.json)
const derived = join(ROOT, 'data', 'derived');
if (existsSync(derived)) {
  mkdirSync(join(PUB, 'data'), { recursive: true });
  cpSync(derived, join(PUB, 'data'), { recursive: true });
  console.log('[copy-data] data/derived -> public/data');
} else {
  console.warn('[copy-data] no data/derived — run scripts/precompute first');
}

// 2) inline the lidar3dlab Python sources for the optional Pyodide live lane -> public/pyodide/sources.json
const pkg = join(ROOT, 'data-pipeline', 'lidar3dlab');
if (existsSync(pkg)) {
  const sources = {};
  const walk = (dir, rel = '') => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      if (e.name === '__pycache__') continue;
      const abs = join(dir, e.name);
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) walk(abs, r);
      else if (e.name.endsWith('.py')) sources[`lidar3dlab/${r}`] = readFileSync(abs, 'utf-8');
    }
  };
  walk(pkg);
  mkdirSync(join(PUB, 'pyodide'), { recursive: true });
  writeFileSync(join(PUB, 'pyodide', 'sources.json'), JSON.stringify(sources));
  console.log(`[copy-data] inlined ${Object.keys(sources).length} lidar3dlab sources -> public/pyodide/sources.json`);
}
