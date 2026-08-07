create table if not exists public.raw_records (
    id bigserial primary key,
    record_key text not null unique,
    run_id text not null,
    source text not null,
    endpoint jsonb,
    city text not null,
    status text not null,
    pipeline_version text not null,
    api_version text,
    retrieved_at timestamptz not null,
    response_time_ms integer not null,
    response_time_seconds double precision,
    error text,
    data_date date,
    raw_payload jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_raw_records_run_id on public.raw_records (run_id);
create index if not exists idx_raw_records_city_date on public.raw_records (city, data_date);
create index if not exists idx_raw_records_source on public.raw_records (source);

