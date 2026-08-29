-- Foundation schema (Phase 1).
--
-- Tenancy model: one caregiver (= one auth.users row) owns many children.
-- Every child-scoped table has RLS enabled with a policy that resolves
-- ownership through children.caregiver_id = auth.uid().
--
-- The backend normally connects with the caregiver's JWT, so these policies
-- are the real access-control boundary. The service-role key bypasses RLS and
-- is used only for the operations listed in
-- app/services/supabase_client.py::ALLOWED_SERVICE_OPERATIONS.

-- ---------------------------------------------------------------------------
-- Enums
-- ---------------------------------------------------------------------------
create type consent_basis as enum ('parent', 'guardian', 'professional_with_parental_consent');
create type media_kind    as enum ('card_icon', 'card_audio', 'schedule_icon', 'rule_audio', 'tts_cache');

-- ---------------------------------------------------------------------------
-- caregivers — the account. 1:1 with auth.users.
-- ---------------------------------------------------------------------------
create table caregivers (
  id                uuid primary key references auth.users (id) on delete cascade,
  display_name      text not null,
  pin_hash          text,                          -- argon2; null until onboarding sets it
  pin_set_at        timestamptz,
  terms_accepted_at timestamptz,
  terms_version     text,
  voice_consent_at  timestamptz,                   -- gates caregiver voice recording UI
  created_at        timestamptz not null default now()
);

alter table caregivers enable row level security;

create policy caregivers_self_select on caregivers
  for select using (id = auth.uid());
create policy caregivers_self_update on caregivers
  for update using (id = auth.uid()) with check (id = auth.uid());
-- insert/delete handled by the backend via the service role (sign-up, erasure).

-- ---------------------------------------------------------------------------
-- children — the subject of care.
-- ---------------------------------------------------------------------------
create table children (
  id                  uuid primary key default gen_random_uuid(),
  caregiver_id        uuid not null references caregivers (id) on delete cascade,
  name                text not null,
  birth_date          date,
  avatar_seed         text,
  consent_basis       consent_basis not null,
  consent_recorded_at timestamptz not null default now(),
  is_active           boolean not null default true,
  created_at          timestamptz not null default now()
);

create index children_caregiver_idx on children (caregiver_id) where is_active;

alter table children enable row level security;

create policy children_owner_all on children
  for all using (caregiver_id = auth.uid()) with check (caregiver_id = auth.uid());

-- ---------------------------------------------------------------------------
-- module_settings — which modules User Mode shows for a child.
-- ---------------------------------------------------------------------------
create table module_settings (
  child_id                uuid primary key references children (id) on delete cascade,
  aac_enabled             boolean not null default true,
  schedule_enabled        boolean not null default true,
  rules_enabled           boolean not null default true,
  calming_enabled         boolean not null default true,
  social_stories_enabled  boolean not null default true,
  reading_writing_enabled boolean not null default true
);

alter table module_settings enable row level security;

create policy module_settings_owner_all on module_settings
  for all using (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  ) with check (
    exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );

-- ---------------------------------------------------------------------------
-- consent_records — append-only audit of what was consented to, and when.
-- ---------------------------------------------------------------------------
create table consent_records (
  id            uuid primary key default gen_random_uuid(),
  caregiver_id  uuid not null references caregivers (id) on delete cascade,
  child_id      uuid references children (id) on delete cascade,
  kind          text not null,                     -- 'terms' | 'voice_recording' | 'professional_attestation'
  terms_version text not null,
  accepted_at   timestamptz not null default now(),
  ip            inet,
  user_agent    text
);

create index consent_records_caregiver_idx on consent_records (caregiver_id);

alter table consent_records enable row level security;

create policy consent_records_owner_select on consent_records
  for select using (caregiver_id = auth.uid());
-- inserts go through the backend (service role) so ip / user_agent are trusted.

-- ---------------------------------------------------------------------------
-- device_sessions — one row per signed-in device; enables remote revocation.
-- ---------------------------------------------------------------------------
create table device_sessions (
  id                uuid primary key default gen_random_uuid(),
  caregiver_id      uuid not null references caregivers (id) on delete cascade,
  device_label      text,
  refresh_token_enc text not null,                 -- Fernet-encrypted; never leaves the backend
  created_at        timestamptz not null default now(),
  last_seen_at      timestamptz not null default now(),
  revoked_at        timestamptz
);

create index device_sessions_caregiver_idx on device_sessions (caregiver_id) where revoked_at is null;

alter table device_sessions enable row level security;

create policy device_sessions_owner_select on device_sessions
  for select using (caregiver_id = auth.uid());
create policy device_sessions_owner_revoke on device_sessions
  for update using (caregiver_id = auth.uid()) with check (caregiver_id = auth.uid());

-- ---------------------------------------------------------------------------
-- media_assets — pointer table for objects in Storage (private buckets).
-- Served to the client only through the stable /api/media/<id> route.
-- ---------------------------------------------------------------------------
create table media_assets (
  id           uuid primary key default gen_random_uuid(),
  child_id     uuid references children (id) on delete cascade,   -- null for shared tts_cache
  kind         media_kind not null,
  storage_path text not null,
  mime         text not null,
  bytes        bigint not null,
  sha256       text not null,
  created_at   timestamptz not null default now()
);

create index media_assets_child_idx on media_assets (child_id);
create unique index media_assets_ttscache_sha_idx
  on media_assets (sha256) where kind = 'tts_cache';

alter table media_assets enable row level security;

create policy media_assets_owner_select on media_assets
  for select using (
    child_id is not null
    and exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid())
  );
-- writes via backend; tts_cache rows (child_id null) are backend-only.

-- ---------------------------------------------------------------------------
-- usage_counters — per caregiver, per calendar month. Quota enforcement.
-- ---------------------------------------------------------------------------
create table usage_counters (
  caregiver_id uuid not null references caregivers (id) on delete cascade,
  period       text not null,                       -- 'YYYY-MM'
  tts_chars    bigint not null default 0,
  image_count  integer not null default 0,
  llm_tokens   bigint not null default 0,
  primary key (caregiver_id, period)
);

alter table usage_counters enable row level security;

create policy usage_counters_owner_select on usage_counters
  for select using (caregiver_id = auth.uid());

-- ---------------------------------------------------------------------------
-- audit_log — sensitive actions (account deletion, PIN reset, revocations,
-- professional consent attestations).
-- ---------------------------------------------------------------------------
create table audit_log (
  id           uuid primary key default gen_random_uuid(),
  caregiver_id uuid references caregivers (id) on delete set null,
  action       text not null,
  target_type  text,
  target_id    uuid,
  detail       jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

create index audit_log_caregiver_idx on audit_log (caregiver_id, created_at desc);

alter table audit_log enable row level security;
-- no policies: readable only via the service role (support / compliance tooling).

-- ---------------------------------------------------------------------------
-- Auto-create the module_settings row for every new child.
-- ---------------------------------------------------------------------------
create function ensure_module_settings() returns trigger
language plpgsql as $$
begin
  insert into module_settings (child_id) values (new.id)
  on conflict (child_id) do nothing;
  return new;
end;
$$;

create trigger children_after_insert
  after insert on children
  for each row execute function ensure_module_settings();
