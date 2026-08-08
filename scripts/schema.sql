-- KMFRI Papyrus Wetland M&E Platform — PostGIS schema
-- Applied via Supabase:apply_migration. Idempotent (IF NOT EXISTS / OR REPLACE throughout).

create extension if not exists postgis;

-- ---------------------------------------------------------------------------
-- Nursery sites (papyrus propagation points feeding restoration polygons)
-- ---------------------------------------------------------------------------
create table if not exists nursery_sites (
    id            bigint generated always as identity primary key,
    site_code     text not null unique,          -- e.g. 'KOR-01'
    site_name     text not null,                  -- e.g. 'Korongo'
    stakeholder   text not null,                  -- NAOFO, LANABLA, KWS, NEMA
    established   date,
    capacity_units integer,                       -- seedling capacity
    geom          geometry(Point, 4326) not null,
    created_at    timestamptz not null default now()
);
create index if not exists idx_nursery_sites_geom on nursery_sites using gist (geom);

-- ---------------------------------------------------------------------------
-- Restoration polygons (papyrus cover — pilot vs target extents, tracked over time)
-- ---------------------------------------------------------------------------
create table if not exists restoration_polygons (
    id              bigint generated always as identity primary key,
    polygon_code    text not null unique,
    phase           text not null check (phase in ('pilot', 'target', 'baseline')),
    area_acres      numeric(10,2) not null,
    nursery_site_id bigint references nursery_sites(id) on delete set null,
    survey_date     date not null,
    cover_pct       numeric(5,2),                 -- papyrus cover % at survey_date
    geom            geometry(Polygon, 4326) not null,
    created_at      timestamptz not null default now()
);
create index if not exists idx_restoration_polygons_geom on restoration_polygons using gist (geom);
create index if not exists idx_restoration_polygons_site on restoration_polygons(nursery_site_id);

-- ---------------------------------------------------------------------------
-- Fish landings (time series, linked to nearest nursery/monitoring site)
-- ---------------------------------------------------------------------------
create table if not exists fish_landings (
    id             bigint generated always as identity primary key,
    site_id        bigint references nursery_sites(id) on delete set null,
    landing_date   date not null,
    species        text not null,                 -- e.g. 'Tilapia', 'Common carp'
    catch_kg       numeric(10,2) not null,
    boats_active   integer,
    created_at     timestamptz not null default now()
);
create index if not exists idx_fish_landings_date on fish_landings(landing_date);
create index if not exists idx_fish_landings_site on fish_landings(site_id);

-- ---------------------------------------------------------------------------
-- Water quality (time series, linked to nearest nursery/monitoring site)
-- ---------------------------------------------------------------------------
create table if not exists water_quality (
    id            bigint generated always as identity primary key,
    site_id       bigint references nursery_sites(id) on delete set null,
    sample_date   date not null,
    turbidity_ntu numeric(6,2),
    ph            numeric(4,2),
    dissolved_o2_mgl numeric(5,2),
    temp_c        numeric(4,1),
    created_at    timestamptz not null default now()
);
create index if not exists idx_water_quality_date on water_quality(sample_date);
create index if not exists idx_water_quality_site on water_quality(site_id);

-- ---------------------------------------------------------------------------
-- RLS: public demo reads allowed via anon key; writes restricted to service role
-- ---------------------------------------------------------------------------
alter table nursery_sites enable row level security;
alter table restoration_polygons enable row level security;
alter table fish_landings enable row level security;
alter table water_quality enable row level security;

drop policy if exists "public read nursery_sites" on nursery_sites;
create policy "public read nursery_sites" on nursery_sites for select using (true);

drop policy if exists "public read restoration_polygons" on restoration_polygons;
create policy "public read restoration_polygons" on restoration_polygons for select using (true);

drop policy if exists "public read fish_landings" on fish_landings;
create policy "public read fish_landings" on fish_landings for select using (true);

drop policy if exists "public read water_quality" on water_quality;
create policy "public read water_quality" on water_quality for select using (true);

-- ---------------------------------------------------------------------------
-- RPC: GeoJSON export functions (called via supabase.rpc() from Python —
-- avoids needing a raw DB connection string / psycopg2 in the app layer)
-- ---------------------------------------------------------------------------
create or replace function nursery_sites_geojson()
returns jsonb
language sql
stable
as $$
  select jsonb_build_object(
    'type', 'FeatureCollection',
    'features', coalesce(jsonb_agg(
      jsonb_build_object(
        'type', 'Feature',
        'geometry', st_asgeojson(geom)::jsonb,
        'properties', jsonb_build_object(
          'id', id, 'site_code', site_code, 'site_name', site_name,
          'stakeholder', stakeholder, 'capacity_units', capacity_units
        )
      )
    ), '[]'::jsonb)
  )
  from nursery_sites;
$$;

create or replace function restoration_polygons_geojson()
returns jsonb
language sql
stable
as $$
  select jsonb_build_object(
    'type', 'FeatureCollection',
    'features', coalesce(jsonb_agg(
      jsonb_build_object(
        'type', 'Feature',
        'geometry', st_asgeojson(geom)::jsonb,
        'properties', jsonb_build_object(
          'id', id, 'polygon_code', polygon_code, 'phase', phase,
          'area_acres', area_acres, 'nursery_site_id', nursery_site_id,
          'survey_date', survey_date, 'cover_pct', cover_pct
        )
      )
    ), '[]'::jsonb)
  )
  from restoration_polygons;
$$;
