"""Water quality time series, optionally filtered by site."""
from __future__ import annotations

import logging
from typing import Any

from services.db import get_client

logger = logging.getLogger(__name__)


def get_water_quality(site_id: int | None = None) -> list[dict[str, Any]]:
    client = get_client()
    try:
        query = client.table("water_quality").select(
            "id, site_id, sample_date, turbidity_ntu, ph, dissolved_o2_mgl, temp_c"
        ).order("sample_date")
        if site_id is not None:
            query = query.eq("site_id", site_id)
        resp = query.execute()
    except Exception:
        logger.exception("Failed to fetch water quality (site_id=%s)", site_id)
        return []
    return resp.data or []
