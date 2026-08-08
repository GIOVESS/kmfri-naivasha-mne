"""Nursery sites & restoration polygons — spatial reads via RPC, tabular via PostgREST."""
from __future__ import annotations

import logging
from typing import Any

from services.db import call_rpc, get_client

logger = logging.getLogger(__name__)


def get_nursery_sites_geojson() -> dict[str, Any]:
    """FeatureCollection of nursery site points."""
    try:
        return call_rpc("nursery_sites_geojson")
    except Exception:
        logger.exception("Failed to fetch nursery_sites_geojson")
        return {"type": "FeatureCollection", "features": []}


def get_restoration_polygons_geojson() -> dict[str, Any]:
    """FeatureCollection of restoration polygons (pilot/target/baseline)."""
    try:
        return call_rpc("restoration_polygons_geojson")
    except Exception:
        logger.exception("Failed to fetch restoration_polygons_geojson")
        return {"type": "FeatureCollection", "features": []}


def get_nursery_site_by_id(site_id: int) -> dict[str, Any] | None:
    client = get_client()
    try:
        resp = client.table("nursery_sites").select("*").eq("id", site_id).limit(1).execute()
    except Exception:
        logger.exception("Failed to fetch nursery site id=%s", site_id)
        return None
    rows = resp.data or []
    return rows[0] if rows else None


def list_nursery_sites() -> list[dict[str, Any]]:
    client = get_client()
    try:
        resp = client.table("nursery_sites").select(
            "id, site_code, site_name, stakeholder, capacity_units"
        ).order("site_name").execute()
    except Exception:
        logger.exception("Failed to list nursery sites")
        return []
    return resp.data or []
