#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi
. .venv/bin/activate
pip install -q -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
