#!/usr/bin/env bash
# Local dev server. Serves API + frontend on :8000 with autoreload.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=./.conda/bin/python
[[ -x "$PY" ]] || PY=python3
exec "$PY" -m flask --app backend/app run --debug --port "${PORT:-8000}"
