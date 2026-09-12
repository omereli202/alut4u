-- Rebrand: rename the two storage.objects deny-policies left over from the
-- "alut4u" name (see 0002_auth.sql). Cosmetic to Postgres — no application
-- code reads policy names — but kept consistent with the rest of the rename.
--
-- Drop + recreate, not ALTER POLICY ... RENAME TO: storage.objects is owned
-- by supabase_storage_admin, and the migration role (postgres) isn't a
-- member of it — confirmed empirically, ALTER POLICY fails with "must be
-- owner of table objects" even though it can create/drop policies on the
-- table (the same mechanism the original 0002_auth.sql policies relied on).
drop policy "alut4u media: no direct client read" on storage.objects;
create policy "omi4u media: no direct client read" on storage.objects
  for select to authenticated, anon using (false);

drop policy "alut4u media: no direct client write" on storage.objects;
create policy "omi4u media: no direct client write" on storage.objects
  for insert to authenticated, anon with check (false);
