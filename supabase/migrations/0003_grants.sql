-- Table-level privileges for the Data API roles.
--
-- Recent Supabase does NOT auto-expose new tables to anon/authenticated/
-- service_role, so RLS policies alone are not enough — the roles also need
-- SQL GRANTs. RLS still does the row-level filtering on top of these.
--
--   service_role  — full access, bypasses RLS (backend system operations only)
--   authenticated — CRUD on app tables; RLS restricts to the caregiver's rows
--   anon          — nothing (the app always calls with a caregiver JWT)

grant usage on schema public to authenticated, service_role;

-- Everything the service role touches.
grant all privileges on all tables in schema public to service_role;
grant all privileges on all sequences in schema public to service_role;
grant all privileges on all functions in schema public to service_role;

-- What a caregiver's JWT may do; RLS narrows it to their own rows.
grant select, insert, update, delete on
  caregivers, children, module_settings, consent_records,
  device_sessions, media_assets, usage_counters
to authenticated;

-- audit_log: no role beyond service_role — it has no RLS policy on purpose.
revoke all on audit_log from anon, authenticated;

-- Future tables (Phase 2+) inherit the same grants automatically.
alter default privileges in schema public
  grant all on tables to service_role;
alter default privileges in schema public
  grant all on sequences to service_role;
alter default privileges in schema public
  grant select, insert, update, delete on tables to authenticated;
