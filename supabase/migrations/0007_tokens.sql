-- Behavior rules + token economy + reward store (Phase 4).
--
-- token_transactions is the append-only source of truth; token_balances is a
-- trigger-maintained running total for cheap reads / User-Mode display.
-- Reward redemption HOLDS the tokens on request (a negative transaction) and
-- refunds them if the caregiver rejects.

-- ---------------------------------------------------------------------------
-- behavior_rules — visual rule cards with an audio explanation.
-- ---------------------------------------------------------------------------
create table behavior_rules (
  id             uuid primary key default gen_random_uuid(),
  child_id       uuid not null references children (id) on delete cascade,
  title          text not null,
  body           text,                         -- the explanation, spoken via tts_asset_id
  symbol_id      text references symbols (id) on delete set null,
  icon_asset_id  uuid references media_assets (id) on delete set null,
  audio_asset_id uuid references media_assets (id) on delete set null,  -- caregiver recording
  tts_asset_id   uuid references media_assets (id) on delete set null,  -- generated from body
  sort_order     integer not null default 0,
  created_at     timestamptz not null default now(),
  constraint behavior_rule_one_visual check (
    (symbol_id is not null)::int + (icon_asset_id is not null)::int <= 1
  )
);
create index behavior_rules_child_idx on behavior_rules (child_id);
alter table behavior_rules enable row level security;
create policy behavior_rules_owner_all on behavior_rules for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

-- ---------------------------------------------------------------------------
-- token_transactions — append-only ledger. balance = sum(delta).
-- kind: 'award' | 'redemption' | 'refund' | 'adjustment' | 'exercise'
-- ---------------------------------------------------------------------------
create table token_transactions (
  id         uuid primary key default gen_random_uuid(),
  child_id   uuid not null references children (id) on delete cascade,
  delta      integer not null,
  kind       text not null,
  reason     text,
  ref_id     uuid,                              -- e.g. the redemption this relates to
  created_by uuid references caregivers (id) on delete set null,
  created_at timestamptz not null default now()
);
create index token_transactions_child_idx on token_transactions (child_id, created_at desc);
alter table token_transactions enable row level security;
create policy token_transactions_owner_all on token_transactions for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

-- ---------------------------------------------------------------------------
-- token_balances — trigger-maintained convenience total.
-- ---------------------------------------------------------------------------
create table token_balances (
  child_id   uuid primary key references children (id) on delete cascade,
  balance    integer not null default 0,
  updated_at timestamptz not null default now()
);
alter table token_balances enable row level security;
create policy token_balances_owner_select on token_balances for select
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

-- SECURITY DEFINER so the balance write runs as the table owner and isn't
-- blocked by RLS (token_balances only exposes a SELECT policy to callers).
create function apply_token_transaction() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into token_balances (child_id, balance, updated_at)
  values (new.child_id, new.delta, now())
  on conflict (child_id) do update
    set balance = token_balances.balance + new.delta, updated_at = now();
  return new;
end;
$$;
create trigger token_transactions_after_insert
  after insert on token_transactions
  for each row execute function apply_token_transaction();

-- ---------------------------------------------------------------------------
-- rewards — the store.
-- ---------------------------------------------------------------------------
create table rewards (
  id            uuid primary key default gen_random_uuid(),
  child_id      uuid not null references children (id) on delete cascade,
  title         text not null,
  cost          integer not null check (cost > 0),
  symbol_id     text references symbols (id) on delete set null,
  icon_asset_id uuid references media_assets (id) on delete set null,
  is_active     boolean not null default true,
  sort_order    integer not null default 0,
  created_at    timestamptz not null default now(),
  constraint reward_one_visual check (
    (symbol_id is not null)::int + (icon_asset_id is not null)::int <= 1
  )
);
create index rewards_child_idx on rewards (child_id) where is_active;
alter table rewards enable row level security;
create policy rewards_owner_all on rewards for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

-- ---------------------------------------------------------------------------
-- reward_redemptions — a request the caregiver approves in the queue.
-- status: 'pending' | 'approved' | 'rejected'
-- ---------------------------------------------------------------------------
create table reward_redemptions (
  id           uuid primary key default gen_random_uuid(),
  child_id     uuid not null references children (id) on delete cascade,
  reward_id    uuid references rewards (id) on delete set null,
  title        text not null,                   -- snapshot
  cost         integer not null,                -- snapshot
  status       text not null default 'pending',
  requested_at timestamptz not null default now(),
  resolved_at  timestamptz,
  resolved_by  uuid references caregivers (id) on delete set null
);
create index reward_redemptions_child_idx on reward_redemptions (child_id, requested_at desc);
create index reward_redemptions_pending_idx on reward_redemptions (status) where status = 'pending';
alter table reward_redemptions enable row level security;
create policy reward_redemptions_owner_all on reward_redemptions for all
  using (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()))
  with check (exists (select 1 from children c where c.id = child_id and c.caregiver_id = auth.uid()));

grant select, insert, update, delete on
  behavior_rules, token_transactions, rewards, reward_redemptions to authenticated;
grant select on token_balances to authenticated;
