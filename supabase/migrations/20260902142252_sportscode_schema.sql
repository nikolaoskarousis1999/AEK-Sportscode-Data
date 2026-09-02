-- ============================================================
-- AEK SPORTSCODE DATA - INITIAL SCHEMA
-- ============================================================


-- ============================================================
-- COMPETITIONS
-- ============================================================

create table public.competitions (
    id bigint generated always as identity primary key,
    name text not null unique
);


-- ============================================================
-- MATCHES
-- ============================================================

create table public.matches (
    id bigint generated always as identity primary key,
    competition_id bigint not null references public.competitions(id),
    match_date date null,
    opponent text not null,
    venue text not null,
    aek_score integer null,
    opponent_score integer null
);


-- ============================================================
-- SPORTSCODE IMPORTS
-- One row per imported Sportscode XML file.
-- ============================================================

create table public.sportscode_imports (
    id bigint generated always as identity primary key,
    match_id bigint not null references public.matches(id) on delete cascade,
    file_name text not null,
    file_type text not null,
    imported_at timestamptz not null default now(),
    file_hash text null
);


-- ============================================================
-- SPORTSCODE EVENTS
-- One Sportscode <instance> = one row.
-- Periods instances will be ignored by the importer.
-- ============================================================

create table public.sportscode_events (
    id bigint generated always as identity primary key,
    match_id bigint not null references public.matches(id) on delete cascade,
    import_id bigint not null references public.sportscode_imports(id) on delete cascade,
    source_instance_id bigint not null,
    code text not null,
    event_family text not null,
    phase text not null,
    start_seconds double precision not null,
    end_seconds double precision not null,

    constraint sportscode_events_import_instance_unique
        unique (import_id, source_instance_id),

    constraint sportscode_events_time_order_check
        check (end_seconds >= start_seconds)
);


-- ============================================================
-- SPORTSCODE EVENT LABELS
-- One Sportscode <label> = one row.
--
-- Optional Sportscode fields are represented by NO ROW.
-- Repeated / multi-value fields are represented by MULTIPLE ROWS
-- with the same event_id + group_key and different label_order.
--
-- group_name_raw / group_key are nullable because Sportscode can
-- export labels that contain <text> but no <group>.
-- ============================================================

create table public.sportscode_event_labels (
    id bigint generated always as identity primary key,
    event_id bigint not null references public.sportscode_events(id) on delete cascade,
    group_name_raw text null,
    group_key text null,
    value_raw text not null,
    value text not null,
    label_order integer not null,

    constraint sportscode_event_labels_order_unique
        unique (event_id, label_order),

    constraint sportscode_event_labels_order_check
        check (label_order > 0)
);


-- ============================================================
-- INDEXES
-- ============================================================

create index matches_competition_id_idx
    on public.matches (competition_id);

create index sportscode_imports_match_id_idx
    on public.sportscode_imports (match_id);

create index sportscode_events_match_id_idx
    on public.sportscode_events (match_id);

create index sportscode_events_import_id_idx
    on public.sportscode_events (import_id);

create index sportscode_events_family_phase_idx
    on public.sportscode_events (event_family, phase);

create index sportscode_event_labels_event_id_idx
    on public.sportscode_event_labels (event_id);

create index sportscode_event_labels_group_key_idx
    on public.sportscode_event_labels (group_key);


-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table public.competitions
enable row level security;

alter table public.matches
enable row level security;

alter table public.sportscode_imports
enable row level security;

alter table public.sportscode_events
enable row level security;

alter table public.sportscode_event_labels
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
-- The Streamlit app uses the Supabase service_role key.
-- RLS remains enabled, while service_role can access the tables.
-- ============================================================

grant select, insert, update, delete
on table
    public.competitions,
    public.matches,
    public.sportscode_imports,
    public.sportscode_events,
    public.sportscode_event_labels
to service_role;


grant usage, select
on all sequences in schema public
to service_role;
