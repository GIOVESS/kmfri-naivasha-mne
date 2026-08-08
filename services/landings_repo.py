"""Fish landings time series, optionally filtered by site."""
from __future__ import annotations

import logging
from typing import Any

from services.db import get_client

logger = logging.getLogger(__name__)


def get_landings(site_id: int | None = None) -> list[dict[str, Any]]:
    client = get_client()
    try:
        query = client.table("fish_landings").select(
            "id, site_id, landing_date, species, catch_kg, boats_active"
        ).order("landing_date")
        if site_id is not None:
            query = query.eq("site_id", site_id)
        resp = query.execute()
    except Exception:
        logger.exception("Failed to fetch fish landings (site_id=%s)", site_id)
        return []
    return resp.data or []
