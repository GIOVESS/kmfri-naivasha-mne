"""
One-off: fetch a recent low-cloud Sentinel-2 L2A scene over the Lake Naivasha
AOI from Earth Search (Element84) and cache it locally as a GeoTIFF for the
demo (services/imagery.py falls back to this file when no live STAC result
is available, e.g. offline demo, or a network-restricted sandbox).

Requires: pystac-client, rasterio (not in requirements.txt — this script is
an operator/dev-time tool, not an app runtime dependency).

    pip install pystac-client rasterio --break-system-packages
    python3 scripts/fetch_imagery_cache.py

If this fails (no network egress to earth-search.aws.element84.com, as in
some sandboxed dev environments), the app still runs — the map/dashboard
just won't have a raster basemap overlay until this cache is populated.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.imagery import NAIVASHA_BBOX, CACHE_PATH, search_latest_scene  # noqa: E402


def main() -> int:
    item = search_latest_scene(NAIVASHA_BBOX)
    if item is None:
        print("No STAC item found (network unavailable or no low-cloud scene in range).")
        print(f"Cache path remains empty: {CACHE_PATH}")
        return 1

    try:
        import rasterio
        from rasterio.merge import merge
    except ImportError:
        print("rasterio not installed. Run: pip install rasterio --break-system-packages")
        return 1

    visual_href = item["assets"].get("visual", {}).get("href")
    if not visual_href:
        print("STAC item has no 'visual' asset; adjust asset key for this collection.")
        return 1

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(visual_href) as src:
        profile = src.profile
        data = src.read()
    with rasterio.open(CACHE_PATH, "w", **profile) as dst:
        dst.write(data)

    print(f"Cached scene {item.get('id')} -> {CACHE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
