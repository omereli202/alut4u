#!/usr/bin/env bash
# Railway "release" phase — runs once per deploy, before the new version takes
# traffic. Applies pending Supabase migrations to the environment's linked
# project.
#
# Requires: SUPABASE_ACCESS_TOKEN, SUPABASE_DB_URL (set per Railway environment).
# If the Supabase CLI isn't present (e.g. first boot), skip rather than fail the
# deploy — migrations can also be applied from CI.
set -euo pipefail

if ! command -v supabase >/dev/null 2>&1; then
  echo "release: supabase CLI not found, skipping migrations"
  exit 0
fi

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  echo "release: SUPABASE_DB_URL not set, skipping migrations"
  exit 0
fi

# The bundled PCS / Boardmaker symbol set is PROPRIETARY and dev-only (see
# frontend/assets/symbols/pcs/LICENSE.md). Its migration is named
# *_pcs_symbols.sql. Never let it reach production without a content licence.
MIGRATIONS_DIR="$(dirname "$0")/../supabase/migrations"
if compgen -G "$MIGRATIONS_DIR"/*_pcs_symbols.sql > /dev/null; then
  if [[ "${APP_ENV:-}" == "production" || "${RAILWAY_ENVIRONMENT_NAME:-}" == "production" ]]; then
    echo "release: REFUSING to apply migrations — a *_pcs_symbols.sql migration is" >&2
    echo "release: present and this is the production environment. The PCS symbol" >&2
    echo "release: set is proprietary and must not ship to production. Remove it" >&2
    echo "release: (see frontend/assets/symbols/pcs/LICENSE.md) before promoting." >&2
    exit 1
  fi
  echo "release: PCS (dev-only) symbol migration present — ok on non-production env"
fi

echo "release: applying migrations"
supabase db push --db-url "$SUPABASE_DB_URL"
echo "release: done"
