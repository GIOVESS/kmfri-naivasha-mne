# System Design — KMFRI Papyrus Wetland M&E Platform

Status: implemented (demo/pilot build). Decisions below are recorded as ADRs;
each can be revisited independently as the platform moves past demo stage.

## ADR-1: Streamlit + embedded Vite/ArcGIS component, not a standalone SPA

**Decision:** Streamlit hosts the app shell (filters, KPIs, Plotly charts);
the map is a custom Streamlit component — a Vite-built bundle using the
ArcGIS Maps SDK for JavaScript, embedded via `streamlit.components.v1`.

**Why:** KMFRI/WWF stakeholders need a shareable, low-ops demo fast.
Streamlit Community Cloud gives free hosting with no infra to manage. A
custom component is the only way to get true ArcGIS JS SDK rendering (vector
tiles, Calcite UI, hit-testing) inside Streamlit — Folium/pydeck don't cover
Esri-specific rendering needs. The component is isolated in
`components/naivasha_map/` with its own `package.json`, so it can be
extracted into a standalone app later without touching `dashboard/` or
`services/`.

**Trade-off accepted:** two build tooling stacks (pip + npm) in one repo.
Mitigated by keeping the component's frontend self-contained and documenting
the dev-mode env vars (`NAIVASHA_MAP_DEV_MODE`, `NAIVASHA_MAP_DEV_URL`) in
`components/naivasha_map/__init__.py`.

## ADR-2: Supabase (Postgres + PostGIS) as sole data store, accessed via PostgREST

**Decision:** `services/db.py` uses `supabase-py` (PostgREST over HTTPS) for
all reads. Geometry-bearing reads go through two Postgres RPC functions
(`nursery_sites_geojson`, `restoration_polygons_geojson`, defined in
`scripts/schema.sql`) that return `ST_AsGeoJSON` output as JSONB. Tabular
reads (fish landings, water quality) use plain PostgREST table queries.

**Why:** The original plan was SQLAlchemy + GeoAlchemy2 over a direct
Postgres connection. That needs the project's database password, which
isn't exposed through the Supabase management tooling used to provision this
project — only the anon/publishable keys are. RPC functions avoid the app
ever needing raw WKB/WKT parsing or a psycopg2 dependency, at the cost of
one function per geometry-bearing table.

**Reversal path:** if a direct connection becomes available (e.g. the
pooled connection string from Project Settings → Database), swap
`services/db.py`'s internals for SQLAlchemy + GeoAlchemy2. The
`sites_repo.py` / `landings_repo.py` / `water_quality_repo.py` interfaces are
the seam — nothing in `dashboard/` needs to change.

**RLS:** all four tables have row-level security enabled with public-`SELECT`
policies (anon key can read, not write). This is correct for a public demo;
before any production write path (admin data entry, survey uploads) is
built, add authenticated-role policies scoped to a service role or Supabase
Auth user, not the anon key.

## ADR-3: Demo-first synthetic data, real schema

**Decision:** `scripts/generate_seed.py` produces synthetic nursery sites,
restoration polygons, and 24-month fish-landings/water-quality time series
with a coherent narrative (pilot restoration at Korongo → gradual fish
landings recovery). `scripts/build_seed_sql.py` turns that into idempotent
`INSERT ... ON CONFLICT` statements for `data/seed/seed_inserts.sql`.

**Why:** Validates the full pipeline (schema → data → map → charts) end to
end before any real KMFRI survey data or Sentinel-2 imagery integration is
in place, so the platform can be pitched and iterated on immediately.

**Reversal path:** replace `data/seed/*.csv`/`*.geojson` with real exports
and re-run `build_seed_sql.py`, or write a small ETL script targeting the
same four tables. Schema (`scripts/schema.sql`) does not need to change for
real data unless new attributes are needed.

## ADR-4: Imagery — live STAC search with local-cache fallback

**Decision:** `services/imagery.py` tries a live STAC search against Earth
Search (Element84) for the most recent low-cloud Sentinel-2 L2A scene over
the Naivasha AOI; on any failure (offline, rate-limited, restricted network
egress) it falls back to a pre-fetched local GeoTIFF at
`data/imagery/naivasha_sentinel2_cache.tif`, populated by
`scripts/fetch_imagery_cache.py`.

**Status:** the cache ships empty in this build — the sandboxed dev
environment used to assemble this repo has no network egress to
`earth-search.aws.element84.com`. Run `fetch_imagery_cache.py` once from an
unrestricted environment (or Streamlit Community Cloud, which does have
general internet egress) to populate it. The app degrades gracefully without
it: no raster overlay, everything else (vector layers, charts, filters)
works.

## Data model

Four tables, all keyed to `nursery_sites` by `site_id`/`nursery_site_id`:

- `nursery_sites` — papyrus propagation points (4 seed rows: Korongo,
  Oserian, Crescent, KWS Annex)
- `restoration_polygons` — pilot/target/baseline extents with `cover_pct`
  per `survey_date`
- `fish_landings` — monthly catch by species per site
- `water_quality` — monthly turbidity/pH/DO/temperature per site

See `scripts/schema.sql` for full DDL, indexes (GiST on geometry columns),
and RLS policies.

## Open items for the next phase

- Direct Postgres connection (ADR-2 reversal) once a DB password is
  available, if query complexity grows beyond what PostgREST/RPC comfortably
  expresses.
- Imagery cache population (ADR-4) from an unrestricted environment.
- Auth-scoped write path for real survey data entry (currently read-only
  demo).
- CI: no test suite yet. Given the small surface (4 repo modules, 3 chart
  functions), unit tests for `dashboard/charts.py` (pure functions, easy to
  test) would be the highest-value first addition.
