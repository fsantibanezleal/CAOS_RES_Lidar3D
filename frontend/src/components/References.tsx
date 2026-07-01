// The shared bibliography (real, verifiable; every entry carries a doi/url). ADR-0017 §4: cite inline with
// <Cite k/> and place a COMPACT <Refs ids={[...]}/> at the END OF EACH SECTION/sub-tab (only that section's
// refs). NEVER a bottom-of-page bibliography dump (the rejected pattern).
export type Ref = { key: string; authors: string; title: string; venue: string; url: string; year: string };

export const REFS: Ref[] = [
  { key: 'lingbot', authors: 'lingbot-map', title: 'Geometric Context Transformer for Streaming 3D Reconstruction', venue: 'arXiv:2604.14141', year: '2026', url: 'https://arxiv.org/abs/2604.14141' },
  { key: 'dust3r', authors: 'Wang et al.', title: 'DUSt3R: Geometric 3D Vision Made Easy', venue: 'CVPR (arXiv:2312.14132)', year: '2024', url: 'https://arxiv.org/abs/2312.14132' },
  { key: 'mast3r', authors: 'Leroy et al.', title: 'Grounding Image Matching in 3D with MASt3R', venue: 'ECCV (arXiv:2406.09756)', year: '2024', url: 'https://arxiv.org/abs/2406.09756' },
  { key: 'vggt', authors: 'Wang et al.', title: 'VGGT: Visual Geometry Grounded Transformer', venue: 'CVPR (arXiv:2503.11651)', year: '2025', url: 'https://arxiv.org/abs/2503.11651' },
  { key: 'dinov2', authors: 'Oquab et al.', title: 'DINOv2: Learning Robust Visual Features without Supervision', venue: 'TMLR (arXiv:2304.07193)', year: '2024', url: 'https://arxiv.org/abs/2304.07193' },
  { key: 'dinov3', authors: 'Siméoni et al.', title: 'DINOv3', venue: 'arXiv:2508.10104', year: '2025', url: 'https://arxiv.org/abs/2508.10104' },
  { key: 'spann3r', authors: 'Wang & Agapito', title: 'Spann3R: 3D Reconstruction with Spatial Memory', venue: '3DV (arXiv:2408.16061)', year: '2025', url: 'https://arxiv.org/abs/2408.16061' },
  { key: 'cut3r', authors: 'Wang et al.', title: 'CUT3R: Continuous 3D Perception with Persistent State', venue: 'CVPR (arXiv:2501.12387)', year: '2025', url: 'https://arxiv.org/abs/2501.12387' },
  { key: 'monst3r', authors: 'Zhang et al.', title: 'MonST3R: Geometry in the Presence of Motion', venue: 'ICLR (arXiv:2410.03825)', year: '2025', url: 'https://arxiv.org/abs/2410.03825' },
  { key: 'fast3r', authors: 'Yang et al.', title: 'Fast3R: 3D Reconstruction of 1000+ Images in One Forward Pass', venue: 'CVPR (arXiv:2501.13928)', year: '2025', url: 'https://arxiv.org/abs/2501.13928' },
  { key: 'mapanything', authors: 'Keetha et al.', title: 'MapAnything: Universal Feed-Forward Metric 3D Reconstruction', venue: 'arXiv:2509.13891', year: '2025', url: 'https://arxiv.org/abs/2509.13891' },
  { key: 'pi3', authors: 'Wang et al.', title: 'Pi3: Permutation-Equivariant Visual Geometry Learning', venue: 'arXiv:2507.13347', year: '2025', url: 'https://arxiv.org/abs/2507.13347' },
  { key: 'vipe', authors: 'NVIDIA', title: 'ViPE: Video Pose Engine for Geometrically-Grounded Video Annotation', venue: 'arXiv:2508.10934', year: '2025', url: 'https://arxiv.org/abs/2508.10934' },
  { key: 'uco3d', authors: 'Liu et al.', title: 'UnCommon Objects in 3D (uCO3D)', venue: 'arXiv:2501.07574', year: '2025', url: 'https://arxiv.org/abs/2501.07574' },
  { key: 'kissicp', authors: 'Vizzo et al.', title: 'KISS-ICP: In Defense of Point-to-Point ICP', venue: 'RA-L (arXiv:2209.15397)', year: '2023', url: 'https://arxiv.org/abs/2209.15397' },
  { key: 'open3d', authors: 'Zhou et al.', title: 'Open3D: A Modern Library for 3D Data Processing', venue: 'arXiv:1801.09847', year: '2018', url: 'https://arxiv.org/abs/1801.09847' },
  { key: 'loam', authors: 'Zhang & Singh', title: 'LOAM: Lidar Odometry and Mapping in Real-time', venue: 'RSS', year: '2014', url: 'https://www.roboticsproceedings.org/rss10/p07.html' },
  { key: 'orbslam3', authors: 'Campos et al.', title: 'ORB-SLAM3: Accurate Visual-Inertial SLAM', venue: 'T-RO (arXiv:2007.11898)', year: '2021', url: 'https://arxiv.org/abs/2007.11898' },
  { key: 'droid', authors: 'Teed & Deng', title: 'DROID-SLAM: Deep Visual SLAM', venue: 'NeurIPS (arXiv:2108.10869)', year: '2021', url: 'https://arxiv.org/abs/2108.10869' },
  { key: 'nerf', authors: 'Mildenhall et al.', title: 'NeRF: Neural Radiance Fields', venue: 'ECCV (arXiv:2003.08934)', year: '2020', url: 'https://arxiv.org/abs/2003.08934' },
  { key: 'gs', authors: 'Kerbl et al.', title: '3D Gaussian Splatting for Real-Time Radiance Field Rendering', venue: 'SIGGRAPH (arXiv:2308.04079)', year: '2023', url: 'https://arxiv.org/abs/2308.04079' },
  { key: 'oxfordspires', authors: 'Tao et al.', title: 'The Oxford Spires Dataset', venue: 'arXiv:2411.10546', year: '2024', url: 'https://arxiv.org/abs/2411.10546' },
  { key: 'kitti', authors: 'Geiger et al.', title: 'Are we ready for Autonomous Driving? The KITTI Benchmark', venue: 'CVPR', year: '2012', url: 'https://www.cvlibs.net/datasets/kitti/' },
  { key: 'tum', authors: 'Sturm et al.', title: 'A Benchmark for the Evaluation of RGB-D SLAM Systems (TUM RGB-D)', venue: 'IROS', year: '2012', url: 'https://cvg.cit.tum.de/data/datasets/rgbd-dataset' },
  { key: 'rope', authors: 'Su et al.', title: 'RoFormer: Enhanced Transformer with Rotary Position Embedding', venue: 'arXiv:2104.09864', year: '2021', url: 'https://arxiv.org/abs/2104.09864' },
  { key: 'flashinfer', authors: 'Ye et al.', title: 'FlashInfer: Efficient Attention Engine for LLM Serving', venue: 'arXiv:2501.01005', year: '2025', url: 'https://arxiv.org/abs/2501.01005' },
];

const BY_KEY: Record<string, Ref> = Object.fromEntries(REFS.map((r) => [r.key, r]));
const numOf = (k: string) => REFS.findIndex((r) => r.key === k) + 1;

// inline citation number, e.g. <Cite k="vggt"/> -> [4] linking to the source
export function Cite({ k }: { k: string }) {
  const r = BY_KEY[k];
  const n = numOf(k);
  return r
    ? <sup className="cite"><a href={r.url} target="_blank" rel="noreferrer" title={`${r.authors}. ${r.title}. ${r.venue} ${r.year}.`}>[{n}]</a></sup>
    : <sup className="cite">[?]</sup>;
}

// compact per-section reference line (ADR-0017 §4): only this section's refs, each linked. Not a page dump.
export function Refs({ ids }: { ids: string[] }) {
  const list = ids.map((k) => BY_KEY[k]).filter(Boolean);
  if (!list.length) return null;
  return (
    <p className="refs-inline">
      <span className="refs-lbl">Refs</span>{' '}
      {list.map((r, i) => (
        <span key={r.key}>{i > 0 ? ' · ' : ''}
          <a href={r.url} target="_blank" rel="noreferrer" title={`${r.title}. ${r.venue} ${r.year}.`}>
            [{numOf(r.key)}] {r.authors} {r.year}
          </a>
        </span>
      ))}
    </p>
  );
}
