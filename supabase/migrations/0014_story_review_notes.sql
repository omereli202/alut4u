-- Story agent crew + text-first / art-after compose.
--
-- compose() now runs a writer -> SLP reviewer -> illustrator crew and saves the
-- reviewed text immediately; illustrations arrive afterwards, one page per
-- request (POST /api/stories/<id>/illustrate). The reviewer's professional
-- notes need to persist alongside the story.
--
-- No new table -> the existing social_stories_owner_all RLS policy and grants
-- already cover these columns.

alter table social_stories
  add column if not exists review_notes jsonb not null default '[]'::jsonb;

comment on column social_stories.pages is
  '[ { "text", "image_prompt", "sentence_type", "image_asset_id": uuid|null, "tts_asset_id": uuid|null } ]';
