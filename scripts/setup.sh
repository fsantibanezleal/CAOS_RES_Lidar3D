#!/usr/bin/env bash
# Create BOTH venvs + install per-lane requirements + the editable package. Idempotent. No global installs.
#   .venv-pipeline = heavy OFFLINE lane (data-pipeline/requirements.txt) + dev + editable pkg  (local-only)
#   .venv          = runtime/live-thin lane (requirements.txt)                                  (what ships)
# Dormant lanes are skipped gracefully. Re-runnable.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python}"

mkvenv() { [ -d "$1" ] || "$PY" -m venv "$1"; }
venvpy() { local p="$1/bin/python"; [ -x "$p" ] || p="$1/Scripts/python.exe"; echo "$p"; }

echo "[setup] .venv-pipeline (offline lane)…"
mkvenv .venv-pipeline
VP="$(venvpy .venv-pipeline)"
"$VP" -m pip install --upgrade pip -q
"$VP" -m pip install -q -r data-pipeline/requirements.txt -r requirements-dev.txt
"$VP" -m pip install -q -e .
echo "[setup] .venv-pipeline ready."

echo "[setup] .venv (runtime/live-thin lane)…"
mkvenv .venv
VR="$(venvpy .venv)"
"$VR" -m pip install --upgrade pip -q
"$VR" -m pip install -q -r requirements.txt
echo "[setup] .venv ready."

echo "[setup] done. Next:  ./scripts/precompute.sh   then   ./scripts/dev.sh"
