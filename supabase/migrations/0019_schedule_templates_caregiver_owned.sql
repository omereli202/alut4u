-- Caregiver-authored schedule templates, alongside the bundled rows from 0017.
--
-- NEW RLS SHAPE for this repo: "global OR mine" — caregiver_id NULL = bundled
-- (readable by everyone), a set caregiver_id = private to that one caregiver.
-- Elsewhere shared/global rows are hidden from clients and served via the
-- service role (see media_assets in 0001), but schedule_templates rows are
-- small, few, and low-risk, so RLS carries the split directly here instead.

alter table schedule_templates
  add column caregiver_id uuid references caregivers (id) on delete cascade;

-- Bundled rows in 0017 set their own literal ids ('home-day', …); caregiver
-- rows need a generated one.
alter table schedule_templates
  alter column id set default gen_random_uuid()::text;

create index schedule_templates_caregiver_idx on schedule_templates (caregiver_id);

drop policy schedule_templates_read on schedule_templates;

create policy schedule_templates_read on schedule_templates
  for select to authenticated
  using (caregiver_id is null or caregiver_id = auth.uid());

create policy schedule_templates_owner_insert on schedule_templates
  for insert to authenticated
  with check (caregiver_id = auth.uid());

create policy schedule_templates_owner_delete on schedule_templates
  for delete to authenticated
  using (caregiver_id = auth.uid());

-- No update policy: caregivers save new templates and delete their own; they
-- do not edit a saved template in place (0017 comment: change bundled rows via
-- a new migration).
grant insert, delete on schedule_templates to authenticated;
