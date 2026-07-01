// The shared bibliography (real, verifiable). Pages cite by key; <References only={[...]}/> renders a numbered
// list. Keep every entry sourced (arXiv id or venue). No invented citations.
export type Ref = { key: string; authors: string; title: string; venue: string; url: string };

export const REFS: Ref[] = [
  { key: 'lingbot', authors: 'lingbot-map', title: 'Geometric Context Transformer for Streaming 3D Reconstruction', venue: 'arXiv:2604.14141, 2026', url: 'https://arxiv.org/abs/2604.14141' },
  { key: 'dust3r', authors: 'Wang et al.', title: 'DUSt3R: Geometric 3D Vision Made Easy', venue: 'CVPR 2024, arXiv:2312.14132', url: 'https://arxiv.org/abs/2312.14132' },
  { key: 'mast3r', authors: 'Leroy et al.', title: 'Grounding Image Matching in 3D with MASt3R', venue: 'ECCV 2024, arXiv:2406.09756', url: 'https://arxiv.org/abs/2406.09756' },
  { key: 'vggt', authors: 'Wang et al.', title: 'VGGT: Visual Geometry Grounded Transformer', venue: 'CVPR 2025, arXiv:2503.11651', url: 'https://arxiv.org/abs/2503.11651' },
  { key: 'dinov2', authors: 'Oquab et al.', title: 'DINOv2: Learning Robust Visual Features without Supervision', venue: 'TMLR 2024, arXiv:2304.07193', url: 'https://arxiv.org/abs/2304.07193' },
  { key: 'dinov3', authors: 'Siméoni et al.', title: 'DINOv3', venue: 'arXiv:2508.10104, 2025', url: 'https://arxiv.org/abs/2508.10104' },
  { key: 'spann3r', authors: 'Wang & Agapito', title: 'Spann3R: 3D Reconstruction with Spatial Memory', venue: '3DV 2025, arXiv:2408.16061', url: 'https://arxiv.org/abs/2408.16061' },
  { key: 'cut3r', authors: 'Wang et al.', title: 'CUT3R: Continuous 3D Perception with Persistent State', venue: 'CVPR 2025, arXiv:2501.12387', url: 'https://arxiv.org/abs/2501.12387' },
  { key: 'monst3r', authors: 'Zhang et al.', title: 'MonST3R: A Simple Approach for Geometry in the Presence of Motion', venue: 'ICLR 2025, arXiv:2410.03825', url: 'https://arxiv.org/abs/2410.03825' },
  { key: 'fast3r', authors: 'Yang et al.', title: 'Fast3R: Towards 3D Reconstruction of 1000+ Images in One Forward Pass', venue: 'CVPR 2025, arXiv:2501.13928', url: 'https://arxiv.org/abs/2501.13928' },
  { key: 'mapanything', authors: 'Keetha et al.', title: 'MapAnything: Universal Feed-Forward Metric 3D Reconstruction', venue: 'arXiv:2509.13891, 2025', url: 'https://arxiv.org/abs/2509.13891' },
  { key: 'pi3', authors: 'Wang et al.', title: 'Pi3: Permutation-Equivariant Visual Geometry Learning', venue: 'arXiv:2507.13347, 2025', url: 'https://arxiv.org/abs/2507.13347' },
  { key: 'vipe', authors: 'NVIDIA', title: 'ViPE: Video Pose Engine for Geometrically-Grounded Video Annotation', venue: 'arXiv:2508.10934, 2025', url: 'https://arxiv.org/abs/2508.10934' },
  { key: 'uco3d', authors: 'Liu et al.', title: 'UnCommon Objects in 3D (uCO3D)', venue: 'arXiv:2501.07574, 2025', url: 'https://arxiv.org/abs/2501.07574' },
  { key: 'kissicp', authors: 'Vizzo et al.', title: 'KISS-ICP: In Defense of Point-to-Point ICP', venue: 'RA-L 2023, arXiv:2209.15397', url: 'https://arxiv.org/abs/2209.15397' },
  { key: 'open3d', authors: 'Zhou et al.', title: 'Open3D: A Modern Library for 3D Data Processing', venue: 'arXiv:1801.09847, 2018', url: 'https://arxiv.org/abs/1801.09847' },
  { key: 'loam', authors: 'Zhang & Singh', title: 'LOAM: Lidar Odometry and Mapping in Real-time', venue: 'RSS 2014', url: 'https://www.roboticsproceedings.org/rss10/p07.html' },
  { key: 'orbslam3', authors: 'Campos et al.', title: 'ORB-SLAM3: An Accurate Open-Source Library for Visual-Inertial SLAM', venue: 'T-RO 2021, arXiv:2007.11898', url: 'https://arxiv.org/abs/2007.11898' },
  { key: 'droid', authors: 'Teed & Deng', title: 'DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras', venue: 'NeurIPS 2021, arXiv:2108.10869', url: 'https://arxiv.org/abs/2108.10869' },
  { key: 'nerf', authors: 'Mildenhall et al.', title: 'NeRF: Representing Scenes as Neural Radiance Fields', venue: 'ECCV 2020, arXiv:2003.08934', url: 'https://arxiv.org/abs/2003.08934' },
  { key: 'gs', authors: 'Kerbl et al.', title: '3D Gaussian Splatting for Real-Time Radiance Field Rendering', venue: 'SIGGRAPH 2023, arXiv:2308.04079', url: 'https://arxiv.org/abs/2308.04079' },
  { key: 'oxfordspires', authors: 'Tao et al.', title: 'The Oxford Spires Dataset: Benchmarking Large-Scale LiDAR-Visual Localisation, Reconstruction and Radiance Field Methods', venue: 'arXiv:2411.10546, 2024', url: 'https://arxiv.org/abs/2411.10546' },
  { key: 'kitti', authors: 'Geiger et al.', title: 'Are we ready for Autonomous Driving? The KITTI Vision Benchmark Suite', venue: 'CVPR 2012', url: 'https://www.cvlibs.net/datasets/kitti/' },
  { key: 'rope', authors: 'Su et al.', title: 'RoFormer: Enhanced Transformer with Rotary Position Embedding', venue: 'arXiv:2104.09864, 2021', url: 'https://arxiv.org/abs/2104.09864' },
  { key: 'flashinfer', authors: 'Ye et al.', title: 'FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving', venue: 'arXiv:2501.01005, 2025', url: 'https://arxiv.org/abs/2501.01005' },
];

const BY_KEY: Record<string, Ref> = Object.fromEntries(REFS.map((r) => [r.key, r]));

// inline citation number, e.g. <Cite k="vggt"/> -> [4]
export function Cite({ k }: { k: string }) {
  const i = REFS.findIndex((r) => r.key === k);
  return <sup className="cite">[{i >= 0 ? i + 1 : '?'}]</sup>;
}

export function References({ only }: { only?: string[] }) {
  const list = only ? only.map((k) => BY_KEY[k]).filter(Boolean) : REFS;
  const numOf = (r: Ref) => REFS.findIndex((x) => x.key === r.key) + 1;
  return (
    <ol className="reflist">
      {list.map((r) => (
        <li key={r.key} value={numOf(r)}>
          {r.authors}. <a href={r.url} target="_blank" rel="noreferrer">{r.title}</a>. <span className="muted">{r.venue}</span>.
        </li>
      ))}
    </ol>
  );
}
