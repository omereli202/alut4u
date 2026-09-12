-- Rebrand: rename the two storage.objects deny-policies left over from the
-- "alut4u" name (see 0002_auth.sql). Cosmetic to Postgres — no application
-- code reads policy names — but kept consistent with the rest of the rename.
alter policy "alut4u media: no direct client read" on storage.objects
  rename to "omi4u media: no direct client read";
alter policy "alut4u media: no direct client write" on storage.objects
  rename to "omi4u media: no direct client write";
