-- Atomic usage-counter increment (Phase 8 hardening).
--
-- Replaces the read-then-write in usage_repo. SECURITY DEFINER so it runs as the
-- table owner; callable only by the service role.

create function bump_usage(
  p_caregiver uuid,
  p_period    text,
  p_tts       bigint,
  p_images    integer,
  p_llm       bigint
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into usage_counters (caregiver_id, period, tts_chars, image_count, llm_tokens)
  values (p_caregiver, p_period, p_tts, p_images, p_llm)
  on conflict (caregiver_id, period) do update
    set tts_chars   = usage_counters.tts_chars  + excluded.tts_chars,
        image_count = usage_counters.image_count + excluded.image_count,
        llm_tokens  = usage_counters.llm_tokens  + excluded.llm_tokens;
end;
$$;

revoke all on function bump_usage(uuid, text, bigint, integer, bigint) from public, anon, authenticated;
grant execute on function bump_usage(uuid, text, bigint, integer, bigint) to service_role;
