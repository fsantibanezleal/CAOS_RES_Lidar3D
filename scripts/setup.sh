#!/usr/bin/env bash
# One-shot environment setup (Python 3.12 .venv + torch cu126 + vendored lingbot-map).
set -e
cd "$(dirname "$0")/.."
py -3.12 -m venv .venv 2>/dev/null || python -m venv .venv
PY=.venv/Scripts/python.exe; [ -f "$PY" ] || PY=.venv/bin/python
"$PY" -m pip install -U pip
"$PY" -m pip install -r requirements.txt
# Heavy engine: torch matching the local driver (560.x -> CUDA 12.6), then vendored lingbot-map.
"$PY" -m pip install torch==2.8.0 torchvision==0.23.0 --index-url https://download.pytorch.org/whl/cu126
"$PY" -m pip install -e third_party/lingbot-map --no-deps
echo "Setup done. Run:  $PY run_app.py   (then http://127.0.0.1:8120)"
