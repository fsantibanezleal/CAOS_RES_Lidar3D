#!/usr/bin/env bash
PDIR="$(cd "$(dirname "$0")" && pwd)"
declare -A P=(
  [2503.11651]="VGGT_visual-geometry-grounded-transformer"
  [2507.13347]="Pi3_permutation-equivariant-recon"
  [2507.02546]="MoGe-2_metric-monocular-geometry"
  [2509.13414]="MapAnything_universal-metric-recon"
  [2501.12387]="CUT3R_continuous-3d-perception"
  [2507.11539]="StreamVGGT_streaming-vggt"
  [2511.10647]="Depth-Anything-3"
  [2312.14132]="DUSt3R_geometric-3d-vision"
  [2406.09756]="MASt3R_matching-stereo-3d"
  [2412.12392]="MASt3R-SLAM_realtime-dense"
  [2408.16061]="Spann3R_spatial-memory"
  [2501.13927]="Fast3R_1000-images-one-pass"
  [2507.18255]="LONG3R_long-sequence-streaming"
  [2507.16443]="VGGT-Long_km-scale"
  [2511.20343]="AMB3R_sparse-volume-backend"
  [2507.14501]="SURVEY_feedforward-3d-recon-view-synthesis"
)
ok=0; fail=0
for id in "${!P[@]}"; do
  out="$PDIR/${id}_${P[$id]}.pdf"
  if [ -s "$out" ]; then echo "skip $id (exists)"; ok=$((ok+1)); continue; fi
  echo "fetch $id -> ${P[$id]}"
  curl -L -s --max-time 120 -o "$out" "https://arxiv.org/pdf/${id}"
  # validate it's a PDF (>50KB and starts %PDF)
  if [ -s "$out" ] && head -c 4 "$out" | grep -q "%PDF"; then ok=$((ok+1)); else echo "  FAILED $id"; rm -f "$out"; fail=$((fail+1)); fi
  sleep 1
done
echo "PAPERS_DONE ok=$ok fail=$fail"
ls -la "$PDIR"/*.pdf | wc -l
