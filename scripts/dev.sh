#!/usr/bin/env bash
cd "$(dirname "$0")/.."
PY=.venv/Scripts/python.exe; [ -f "$PY" ] || PY=.venv/bin/python
exec "$PY" run_app.py
