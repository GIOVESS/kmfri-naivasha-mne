# KMFRI Papyrus Wetland M&E Platform

GIS-based monitoring & evaluation tool for KMFRI (funded by WWF), tracking
papyrus wetland restoration at Lake Naivasha and its relationship to fish
landings. Built by GIOSPATIAL.

Map: ArcGIS Maps SDK for JavaScript (Calcite UI), embedded in Streamlit via a
custom Vite-built component. Data: Supabase (Postgres + PostGIS). Charts:
Plotly. See `system-design.md` for the full architecture decision record.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Secrets (Supabase URL/anon key, ArcGIS API key) are already populated in
`.streamlit/secrets.toml` for this demo project. For a fresh deployment,
copy that file's structure and fill in your own project's keys.

**ArcGIS API key note:** the key currently in `secrets.toml` has the shape of
a short-lived OAuth access token, not a permanent Location Platform API key.
If the map stops authenticating, generate a standing API key from the ArcGIS
developer dashboard and swap it in.

## Project layout

```
app.py                      Streamlit entrypoint
dashboard/                  Page layout, filters, Plotly chart functions
services/                   Data access (Supabase/PostgREST) + imagery
components/naivasha_map/    Custom Streamlit component (Vite + ArcGIS JS SDK)
scripts/                    Schema DDL, seed data generation, imagery fetch
data/seed/                  Synthetic seed data (GeoJSON/CSV) + generated SQL
data/imagery/               Cached Sentinel-2 scene (ships empty — see below)
system-design.md            Architecture Decision Record
```

## Rebuilding the map component

The frontend is already built (`components/naivasha_map/frontend/dist/`). To
rebuild after changing `frontend/src/*.js`:

```bash
cd components/naivasha_map/frontend
npm install   # only needed if node_modules isn't present
npm run build
```

For live-reload development instead of rebuilding on every change:

```bash
cd components/naivasha_map/frontend && npm run dev
```

then run Streamlit with `NAIVASHA_MAP_DEV_MODE=1` set in the environment.

## Re-seeding the database

Schema and seed data already live in the connected Supabase project. To
regenerate synthetic data or point at a different project:

```bash
python3 scripts/generate_seed.py      # writes data/seed/*.geojson, *.csv
python3 scripts/build_seed_sql.py     # writes data/seed/seed_inserts.sql
# then run scripts/schema.sql and data/seed/seed_inserts.sql against your
# Supabase project (SQL editor, or Supabase:execute_sql / apply_migration)
```

## Imagery cache

`data/imagery/` ships empty in this build — see `data/imagery/.README` and
`scripts/fetch_imagery_cache.py`. The app runs fine without it; it just won't
show a Sentinel-2 raster overlay until the cache is populated from an
environment with network access to Earth Search (Element84).

## Basemap — demo vs. Phase 1

The map currently uses free CARTO Dark Matter tiles (no API key required).
This is a demo-stage choice for reliability, not a placeholder for something
broken — see `system-design.md` ADR-5. A fully authoritative, custom-digitized
basemap (verified papyrus extent, gazetted boundaries, surveyed residential/
road layers) needs an Esri Creator seat and real digitization work; that's
scoped as a Phase 1 deliverable.

## Deploying

Push to a GitHub repo and deploy via Streamlit Community Cloud, pointing it
at `app.py`. Add the contents of `.streamlit/secrets.toml` to the app's
Secrets in the Community Cloud dashboard rather than committing the file —
`.gitignore` already excludes it.
