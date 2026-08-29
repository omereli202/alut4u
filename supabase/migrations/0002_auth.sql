-- Auth support (Phase 1): PIN lockout state, server-side session material,
-- Caregiver-Mode elevation, and Storage RLS.

-- ---------------------------------------------------------------------------
-- caregivers: escalating PIN lockout (per account, across devices).
-- ---------------------------------------------------------------------------
alter table caregivers
  add column pin_failed_attempts integer not null default 0,
  add column pin_locked_until    timestamptz;

-- ---------------------------------------------------------------------------
-- device_sessions: everything the backend needs to act as this caregiver,
-- plus the Caregiver-Mode elevation window. Tokens are Fernet-encrypted by the
-- app before they are written here; RLS keeps them unreadable anyway.
-- ---------------------------------------------------------------------------
alter table device_sessions
  add column access_token_enc        text,
  add column access_token_expires_at timestamptz,
  add column elevated_until          timestamptz,
  add column user_agent              text,
  add column ip                      inet;

-- The backend reads/writes device_sessions with the service role (it needs the
-- row before it has a user JWT). No SELECT policy exists for it, so a caregiver
-- JWT cannot read token material even if the anon key leaked.

-- ---------------------------------------------------------------------------
-- Storage RLS — buckets are private; objects are reached only through the
-- backend's /api/media/<id> route, which uses the service role. Deny all
-- direct client access.
-- ---------------------------------------------------------------------------
-- storage.objects already has RLS enabled by Supabase. Add explicit denies so
-- intent is on the record and a future permissive policy can't slip through.
create policy "alut4u media: no direct client read" on storage.objects
  for select to authenticated, anon using (false);
create policy "alut4u media: no direct client write" on storage.objects
  for insert to authenticated, anon with check (false);
