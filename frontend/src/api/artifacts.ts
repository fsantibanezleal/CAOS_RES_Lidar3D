// Fetch the committed artifacts (copied into public/data by copy-data.mjs). Works against the static site OR,
// if app/ is activated, you can repoint these to the API — same shapes (CONTRACT 2).
import type { CaseIndex, CaseManifest, Trace } from '../lib/contract.types';

const base = import.meta.env.BASE_URL;

async function getJSON<T>(rel: string): Promise<T> {
  const res = await fetch(`${base}data/${rel}`);
  if (!res.ok) throw new Error(`fetch ${rel}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const loadIndex = (): Promise<CaseIndex> => getJSON<CaseIndex>('manifests/index.json');
export const loadManifest = (caseId: string): Promise<CaseManifest> =>
  getJSON<CaseManifest>(`manifests/${caseId}.json`);
export const loadTrace = (artifactPath: string): Promise<Trace> => getJSON<Trace>(artifactPath);
