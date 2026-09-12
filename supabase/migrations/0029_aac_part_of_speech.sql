-- Part-of-speech colour coding for AAC cards (Modified Fitzgerald Key,
-- softened palette — frontend/css/tokens.css's --pos-* tokens).
--
-- This is deliberately a column on the CARD, not the category: a root-level
-- core word (e.g. "רוצה") has no category at all, and the whole point of the
-- colour key is that a word keeps the same colour wherever it appears on the
-- board, independent of which folder (if any) holds it. Category colour
-- (aac_categories.color) is unaffected and still used for folder tiles and as
-- the fallback for a card with no part_of_speech set —
-- frontend/js/modules/aac/board.js's tileColor() resolves
-- part_of_speech -> category colour -> none, in that order.
alter table aac_cards add column if not exists part_of_speech text;

alter table aac_cards add constraint aac_cards_pos_valid check (
  part_of_speech is null or part_of_speech in (
    'pronoun', 'verb', 'adjective', 'noun', 'social', 'question',
    'negation', 'little', 'adverb'
  )
);
