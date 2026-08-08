"""Read data/seed/*.geojson and *.csv, emit idempotent INSERT SQL for Supabase."""
import csv
import json
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
OUT_PATH = SEED_DIR / "seed_inserts.sql"

lines = ["-- Auto-generated from data/seed/*. Idempotent via ON CONFLICT.", ""]

# 1. nursery_sites
sites_fc = json.loads((SEED_DIR / "nursery_sites.geojson").read_text())
lines.append("-- nursery_sites")
for f in sites_fc["features"]:
    p = f["properties"]
    lon, lat = f["geometry"]["coordinates"]
    established = f"'{p['established']}'" if p.get("established") else "NULL"
    lines.append(
        f"INSERT INTO public.nursery_sites (site_code, site_name, stakeholder, established, "
        f"capacity_units, geom) VALUES ('{p['site_code']}', '{p['site_name']}', '{p['stakeholder']}', "
        f"{established}, {p['capacity_units']}, ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)) "
        f"ON CONFLICT (site_code) DO UPDATE SET geom = EXCLUDED.geom;"
    )
lines.append("")

# 2. restoration_polygons (need nursery_site_id lookup by site_code via subquery)
polys_fc = json.loads((SEED_DIR / "restoration_polygons.geojson").read_text())
lines.append("-- restoration_polygons")
for f in polys_fc["features"]:
    p = f["properties"]
    ring = f["geometry"]["coordinates"][0]
    ring_sql = ", ".join(f"{lon} {lat}" for lon, lat in ring)
    lines.append(
        f"INSERT INTO public.restoration_polygons (polygon_code, phase, area_acres, nursery_site_id, "
        f"survey_date, cover_pct, geom) VALUES ('{p['polygon_code']}', '{p['phase']}', {p['area_acres']}, "
        f"(SELECT id FROM public.nursery_sites WHERE site_code = '{p['site_code']}'), "
        f"'{p['survey_date']}', {p['cover_pct']}, "
        f"ST_SetSRID(ST_GeomFromText('POLYGON(({ring_sql}))'), 4326)) "
        f"ON CONFLICT (polygon_code) DO UPDATE SET cover_pct = EXCLUDED.cover_pct;"
    )
lines.append("")

# 3. fish_landings
lines.append("-- fish_landings")
with open(SEED_DIR / "fish_landings_synthetic.csv") as fh:
    for row in csv.DictReader(fh):
        lines.append(
            f"INSERT INTO public.fish_landings (site_id, landing_date, species, catch_kg, boats_active) "
            f"VALUES ((SELECT id FROM public.nursery_sites WHERE site_code = '{row['site_code']}'), "
            f"'{row['landing_date']}', '{row['species']}', {row['catch_kg']}, {row['boats_active']});"
        )
lines.append("")

# 4. water_quality
lines.append("-- water_quality")
with open(SEED_DIR / "water_quality_synthetic.csv") as fh:
    for row in csv.DictReader(fh):
        lines.append(
            f"INSERT INTO public.water_quality (site_id, sample_date, turbidity_ntu, ph, "
            f"dissolved_o2_mgl, temp_c) VALUES ("
            f"(SELECT id FROM public.nursery_sites WHERE site_code = '{row['site_code']}'), "
            f"'{row['sample_date']}', {row['turbidity_ntu']}, {row['ph']}, "
            f"{row['dissolved_o2_mgl']}, {row['temp_c']});"
        )

OUT_PATH.write_text("\n".join(lines))
print(f"Wrote {OUT_PATH} ({len(lines)} lines)")
