"""
Generate synthetic seed data for the KMFRI M&E demo:
- nursery_sites.geojson (4 points)
- restoration_polygons.geojson (pilot/target/baseline squares sized to acreage)
- fish_landings_synthetic.csv (24 months x 4 sites x 2 species)
- water_quality_synthetic.csv (24 months x 4 sites)

Also emits seed_insert.sql with ready-to-run INSERT statements (run via
Supabase execute_sql / apply_migration since RLS blocks anon-key writes
by design — this is an admin-side seed operation, not app traffic).
"""
import csv
import json
import math
import random
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "seed"
DATA_DIR.mkdir(parents=True, exist_ok=True)

M_PER_DEG = 111_300  # approx at the equator, fine for this latitude

SITES = [
    {"site_code": "KOR-01", "site_name": "Korongo", "stakeholder": "NAOFO",
     "established": "2022-03-01", "capacity_units": 5000, "lon": 36.361, "lat": -0.744},
    {"site_code": "OSE-01", "site_name": "Oserian", "stakeholder": "LANABLA",
     "established": "2021-11-15", "capacity_units": 8000, "lon": 36.280, "lat": -0.750},
    {"site_code": "CRE-01", "site_name": "Crescent", "stakeholder": "KWS",
     "established": "2023-01-10", "capacity_units": 3000, "lon": 36.371, "lat": -0.780},
    {"site_code": "KWS-ANX", "site_name": "KWS Annex", "stakeholder": "NEMA",
     "established": "2022-07-20", "capacity_units": 4000, "lon": 36.360, "lat": -0.729},
]

def square_polygon(lon, lat, acres, offset_lon=0.0, offset_lat=0.0):
    area_m2 = acres * 4046.86
    side_m = math.sqrt(area_m2)
    side_deg = side_m / M_PER_DEG
    half = side_deg / 2
    cx, cy = lon + offset_lon, lat + offset_lat
    coords = [
        [cx - half, cy - half],
        [cx + half, cy - half],
        [cx + half, cy + half],
        [cx - half, cy + half],
        [cx - half, cy - half],
    ]
    return coords

POLYGONS = [
    {"polygon_code": "PIL-30", "phase": "pilot", "area_acres": 30.0,
     "site_code": "KOR-01", "survey_date": "2025-06-01", "cover_pct": 62.0,
     "offset": (0.006, 0.004)},
    {"polygon_code": "TGT-100", "phase": "target", "area_acres": 100.0,
     "site_code": "OSE-01", "survey_date": "2025-06-01", "cover_pct": 28.0,
     "offset": (0.008, -0.003)},
    {"polygon_code": "BASE-15", "phase": "baseline", "area_acres": 15.0,
     "site_code": "CRE-01", "survey_date": "2024-01-01", "cover_pct": 12.0,
     "offset": (-0.005, 0.005)},
]

SPECIES = ["Tilapia", "Common carp"]

# --- nursery_sites.geojson ---
sites_fc = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {k: v for k, v in s.items() if k not in ("lon", "lat")},
        }
        for s in SITES
    ],
}
(DATA_DIR / "nursery_sites.geojson").write_text(json.dumps(sites_fc, indent=2))

# --- restoration_polygons.geojson ---
site_by_code = {s["site_code"]: s for s in SITES}
polys_fc = {"type": "FeatureCollection", "features": []}
for p in POLYGONS:
    s = site_by_code[p["site_code"]]
    coords = square_polygon(s["lon"], s["lat"], p["area_acres"], *p["offset"])
    polys_fc["features"].append({
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": {
            "polygon_code": p["polygon_code"], "phase": p["phase"],
            "area_acres": p["area_acres"], "site_code": p["site_code"],
            "survey_date": p["survey_date"], "cover_pct": p["cover_pct"],
        },
    })
(DATA_DIR / "restoration_polygons.geojson").write_text(json.dumps(polys_fc, indent=2))

# --- fish_landings_synthetic.csv (24 months, Jan 2024 - Dec 2025) ---
# Narrative: landings dip through 2024 (wetland degradation), recover through 2025
# as pilot restoration (Korongo) takes hold; Oserian/target site lags.
landings_rows = []
for month_idx in range(24):
    year = 2024 + month_idx // 12
    month = month_idx % 12 + 1
    date = f"{year}-{month:02d}-01"
    for s in SITES:
        recovery_factor = 1.0
        if s["site_code"] == "KOR-01" and month_idx >= 12:
            recovery_factor = 1.0 + 0.03 * (month_idx - 12)  # steady recovery post-pilot
        elif month_idx < 12:
            recovery_factor = 1.0 - 0.02 * month_idx  # pre-restoration decline
        for species in SPECIES:
            base_kg = 850 if species == "Tilapia" else 400
            noise = random.uniform(0.85, 1.15)
            catch_kg = round(base_kg * recovery_factor * noise, 1)
            boats = random.randint(6, 18)
            landings_rows.append([s["site_code"], date, species, catch_kg, boats])

with open(DATA_DIR / "fish_landings_synthetic.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["site_code", "landing_date", "species", "catch_kg", "boats_active"])
    writer.writerows(landings_rows)

# --- water_quality_synthetic.csv (24 months) ---
wq_rows = []
for month_idx in range(24):
    year = 2024 + month_idx // 12
    month = month_idx % 12 + 1
    date = f"{year}-{month:02d}-01"
    for s in SITES:
        improve = 0.01 * month_idx if s["site_code"] == "KOR-01" else 0.003 * month_idx
        turbidity = round(max(5.0, 35 - improve * 20 + random.uniform(-3, 3)), 1)
        ph = round(7.2 + random.uniform(-0.3, 0.3), 2)
        do = round(min(9.0, 4.5 + improve * 15 + random.uniform(-0.4, 0.4)), 2)
        temp = round(22 + random.uniform(-1.5, 1.5), 1)
        wq_rows.append([s["site_code"], date, turbidity, ph, do, temp])

with open(DATA_DIR / "water_quality_synthetic.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["site_code", "sample_date", "turbidity_ntu", "ph", "dissolved_o2_mgl", "temp_c"])
    writer.writerows(wq_rows)

print("Seed files written to", DATA_DIR)
for f in DATA_DIR.iterdir():
    print(" -", f.name)
