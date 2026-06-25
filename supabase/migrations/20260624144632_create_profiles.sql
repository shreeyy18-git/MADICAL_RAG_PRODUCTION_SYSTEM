create table if not exists profiles (
    user_id uuid primary key references auth.users(id) on delete cascade,
    name text not null default '',
    age integer,
    phone text not null default '',
    older_disease text not null default '',
    updated_at timestamptz not null default now()
);

alter table profiles enable row level security;

create policy "Users manage their own profile"
    on profiles for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
