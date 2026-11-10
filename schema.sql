-- ============================================
-- جدول کاربران
-- ============================================
create table if not exists users (
  telegram_id bigint primary key,
  username text,
  phone_verified boolean default false,
  referred_by bigint,
  balance_ton numeric default 0,
  balance_tron numeric default 0,
  balance_dogez numeric default 0,
  balance_tether numeric default 0,
  balance_not numeric default 0,
  balance_stars numeric default 0,
  joined_at timestamptz default now()
);

-- ============================================
-- جدول تراکنش‌ها
-- ============================================
create table if not exists transactions (
  id bigserial primary key,
  telegram_id bigint,
  type text,
  currency text,
  amount numeric,
  fee numeric default 0,
  status text default 'pending',
  tx_hash text,
  extra text,
  created_at timestamptz default now()
);

-- ============================================
-- جدول وضعیت موقت کاربر
-- ============================================
create table if not exists user_states (
  telegram_id bigint primary key,
  state text,
  data jsonb default '{}'::jsonb
);

-- ============================================
-- جدول ایردراپ‌ها
-- ============================================
create table if not exists airdrops (
  id bigserial primary key,
  owner_id bigint,
  capacity int default 0,
  joined int default 0,
  require_phone boolean default false,
  require_captcha boolean default false,
  reward_amount numeric default 0,
  join_reward numeric default 0,
  currency text default 'dogez',
  code text unique,
  active boolean default true,
  created_at timestamptz default now()
);

-- ============================================
-- جدول شرکت‌کنندگان ایردراپ
-- ============================================
create table if not exists airdrop_joins (
  id bigserial primary key,
  airdrop_id bigint references airdrops(id) on delete cascade,
  telegram_id bigint,
  joined_at timestamptz default now(),
  unique(airdrop_id, telegram_id)
);

-- ============================================
-- ایندکس‌ها
-- ============================================
create index if not exists idx_transactions_telegram_id on transactions(telegram_id);
create index if not exists idx_transactions_type on transactions(type);
create index if not exists idx_transactions_status on transactions(status);
create index if not exists idx_airdrops_owner on airdrops(owner_id);
create index if not exists idx_airdrops_code on airdrops(code);
create index if not exists idx_airdrop_joins_ad on airdrop_joins(airdrop_id);

-- ============================================
-- امنیت (RLS)
-- ============================================
alter table users enable row level security;
alter table transactions enable row level security;
alter table user_states enable row level security;
alter table airdrops enable row level security;
alter table airdrop_joins enable row level security;

create policy "service_role_all_users" on users for all using (auth.role() = 'service_role');
create policy "service_role_all_tx" on transactions for all using (auth.role() = 'service_role');
create policy "service_role_all_states" on user_states for all using (auth.role() = 'service_role');
create policy "service_role_all_airdrops" on airdrops for all using (auth.role() = 'service_role');
create policy "service_role_all_joins" on airdrop_joins for all using (auth.role() = 'service_role');
