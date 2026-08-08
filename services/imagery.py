"""
Sentinel-2 imagery access for the Naivasha AOI.

Demo strategy: try a live STAC search against Earth Search (Element84);
on any failure (rate limit, offline, no network egress) fall back to the
pre-fetched cache at data/imagery/naivasha_sentinel2_cache.tif, generated
by scripts/fetch_imagery_cache.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STAC_ENDPOINT = "https://earth-search.aws.element84.com/v1"
COLLECTION = "sentinel-2-l2a"

# Lake Naivasha AOI bounding box (WGS84)
NAIVASHA_BBOX = [36.20, -0.85, 36.45, -0.65]

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "imagery" / "naivasha_sentinel2_cache.tif"


def search_latest_scene(bbox: list[float] = NAIVASHA_BBOX, max_cloud: int = 20) -> dict | None:
    """Query STAC for the most recent low-cloud Sentinel-2 scene over the AOI."""
    try:
        from pystac_client import Client
    except ImportError:
        logger.warning("pystac_client not installed — skipping live STAC search")
        return None

    try:
        catalog = Client.open(STAC_ENDPOINT)
        search = catalog.search(
            collections=[COLLECTION],
            bbox=bbox,
            query={"eo:cloud_cover": {"lt": max_cloud}},
            sortby=[{"field": "properties.datetime", "direction": "desc"}],
            max_items=1,
        )
        items = list(search.items())
    except Exception:
        logger.exception("STAC search failed, will fall back to cache")
        return None

    if not items:
        return None
    return items[0].to_dict()


def get_scene_or_cache() -> Path | dict:
    """Return a live STAC item dict if available, else the local cache path."""
    item = search_latest_scene()
    if item is not None:
        return item
    if CACHE_PATH.exists():
        logger.info("Using cached Sentinel-2 scene: %s", CACHE_PATH)
        return CACHE_PATH
    logger.warning(
        "No live STAC result and no cache at %s — run scripts/fetch_imagery_cache.py",
        CACHE_PATH,
    )
    return CACHE_PATH
