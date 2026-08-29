#!/usr/bin/env bash
# Local dev: one Flask process serves the API AND the PWA on :8000 (autoreload).
# Production splits these into a backend + a Caddy frontend service — see
# docs/deployment.md.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=./.conda/bin/python
[[ -x "$PY" ]] || PY=python3
export SERVE_FRONTEND=1
exec "$PY" -m flask --app backend/app run --debug --port "${PORT:-8000}"
