create table if not exists public.ml_ready_records (
    id bigserial primary key,
    record_key text not null unique,
    timestamp timestamptz not null,
    data_date date not null,
    city text not null,
    latitude double precision,
    longitude double precision,
    temperature double precision,
    humidity double precision,
    pressure double precision,
    wind_speed double precision,
    wind_direction double precision,
    cloud_cover double precision,
    rain double precision,
    pm25 double precision,
    pm10 double precision,
    co double precision,
    no double precision,
    no2 double precision,
    so2 double precision,
    o3 double precision,
    nh3 double precision,
    aqi double precision,
    created_at timestamptz not null default now()
);

create index if not exists idx_ml_ready_records_city_date on public.ml_ready_records (city, data_date);
create index if not exists idx_ml_ready_records_timestamp on public.ml_ready_records (timestamp);
