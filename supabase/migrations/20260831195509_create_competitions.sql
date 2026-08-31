-- ============================================================
-- COMPETITIONS
-- ============================================================

create table public.competitions (
    id bigint generated always as identity primary key,
    name text not null unique
);


-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table public.competitions
enable row level security;


-- ============================================================
-- INITIAL DATA
-- ============================================================

insert into public.competitions (
    name
)
values
    ('Super League'),
    ('Greek Cup'),
    ('Champions League');


-- ============================================================
-- DATA API PERMISSIONS
-- ============================================================

grant select, insert, update, delete
on table public.competitions
to service_role;


grant usage, select
on all sequences in schema public
to service_role;