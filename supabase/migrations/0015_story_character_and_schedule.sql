-- Story crew refinements:
--   character_sheet — one English description of the protagonist the illustrator
--     writes at compose time and every page image is drawn from, so the child
--     stays the same person across pages.
--   schedule — when the event happens, collected in the interview and stated in
--     the story's opening line.
--
-- No new table -> the existing social_stories_owner_all RLS policy and grants
-- already cover these columns.

alter table social_stories
  add column if not exists character_sheet text,
  add column if not exists schedule       text;
