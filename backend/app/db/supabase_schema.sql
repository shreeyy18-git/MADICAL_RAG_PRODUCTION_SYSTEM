-- Run this in the Supabase SQL editor for your project.
-- Tables are scoped to auth.users via Row Level Security so each user
-- only ever sees their own conversations, messages, documents, and memory.

create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    created_at timestamptz not null default now()
);

create table if not exists messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references conversations(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    created_at timestamptz not null default now()
);

create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    storage_path text not null,
    chunk_count integer not null default 0,
    uploaded_by uuid references auth.users(id) on delete set null,
    created_at timestamptz not null default now()
);

-- Phase 2: long-term memory facts
create table if not exists memory_facts (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    fact_text text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_messages_conversation on messages(conversation_id, created_at);
create index if not exists idx_conversations_user on conversations(user_id);
create index if not exists idx_documents_uploaded_by on documents(uploaded_by);
create index if not exists idx_memory_facts_user on memory_facts(user_id);

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

alter table conversations enable row level security;
alter table messages enable row level security;
alter table documents enable row level security;
alter table memory_facts enable row level security;

create policy "Users manage their own conversations"
    on conversations for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

create policy "Users manage messages in their own conversations"
    on messages for all
    using (exists (
        select 1 from conversations c
        where c.id = messages.conversation_id and c.user_id = auth.uid()
    ));

create policy "All authenticated users can view documents"
    on documents for select
    using (auth.role() = 'authenticated');

create policy "Authenticated users can insert documents"
    on documents for insert
    with check (auth.role() = 'authenticated');

create policy "Users manage their own memory facts"
    on memory_facts for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- Create the storage bucket for source PDFs (run once):
-- insert into storage.buckets (id, name, public) values ('medical-documents', 'medical-documents', false);
