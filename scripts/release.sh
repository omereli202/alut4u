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

echo "release: applying migrations"
supabase db push --db-url "$SUPABASE_DB_URL"
echo "release: done"
