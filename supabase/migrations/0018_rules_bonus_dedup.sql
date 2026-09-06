-- Once-a-day guard for the rules daily bonus.
--
-- The caregiver grants the bonus by hand (from the caregiver editor, or from a
-- PIN-gated button on the child's own rules page). Both paths hit
-- POST /api/tokens/rules/bonus, which refuses a second grant on the same day.
-- "Day" is the caller's LOCAL date, sent by the client (same pattern as the
-- schedule module's ?date=) — there is no server-side timezone.

alter table rules_settings add column if not exists last_bonus_date date;
