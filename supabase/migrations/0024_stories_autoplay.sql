-- Social stories: auto-read (TTS) toggle.
--
-- A playback preference, NOT a module flag: it does not gate a User-Mode tile
-- and does not appear in the caregiver dashboard's module toggle list (both of
-- those lists are explicit). The caregiver flips it inside the story editor.
-- When true (default) the reader speaks each page on open and on every page
-- turn; when false the child taps "הקראה" to hear a page.
--
-- Lives on module_settings so it rides the existing per-child RLS policy
-- (precedent: 0023_typing_board.sql adds a column to module_settings the same
-- way).

alter table module_settings
  add column stories_autoplay boolean not null default true;
