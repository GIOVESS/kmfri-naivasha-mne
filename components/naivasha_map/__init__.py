"""
Streamlit custom component wrapper for the ArcGIS Maps SDK for JavaScript
map view (Vite-built frontend in ./frontend).

Declared in "release" mode by default (serves the built dist/ bundle).
Set NAIVASHA_MAP_DEV_MODE=1 to point at the Vite dev server instead
(useful when iterating on frontend/src without rebuilding each time).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

_DEV_MODE = os.environ.get("NAIVASHA_MAP_DEV_MODE") == "1"
_DEV_URL = os.environ.get("NAIVASHA_MAP_DEV_URL", "http://localhost:5173")
_BUILD_DIR = Path(__file__).parent / "frontend" / "dist"

if _DEV_MODE:
    _component_func = components.declare_component("naivasha_map", url=_DEV_URL)
else:
    _component_func = components.declare_component("naivasha_map", path=str(_BUILD_DIR))


def naivasha_map(
    nursery_sites: dict[str, Any],
    restoration_polygons: dict[str, Any],
    selected_site_id: int | None = None,
    height: int = 600,
    key: str | None = None,
) -> dict[str, Any] | None:
    """
    Render the ArcGIS MapView. Returns the last value passed to
    Streamlit.setComponentValue() by bridge.js — e.g. {"site_id": 3}
    when the user clicks a nursery site marker.
    """
    try:
        arcgis_api_key = st.secrets["arcgis"]["api_key"]
    except KeyError:
        st.error("Missing [arcgis] api_key in .streamlit/secrets.toml")
        arcgis_api_key = ""

    component_value = _component_func(
        nurserySites=nursery_sites,
        restorationPolygons=restoration_polygons,
        selectedSiteId=selected_site_id,
        arcgisApiKey=arcgis_api_key,
        height=height,
        key=key,
        default=None,
    )
    return component_value
