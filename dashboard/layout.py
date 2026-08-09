"""Page structure: map (left) + KPI/charts (right), site filter synced from map clicks."""
from __future__ import annotations

import logging

import streamlit as st

from components.naivasha_map import naivasha_map
from dashboard import charts
from dashboard.filters import get_selected_site_id, sync_from_map_component
from services.landings_repo import get_landings
from services.sites_repo import get_nursery_site_by_id, get_nursery_sites_geojson, \
    get_restoration_polygons_geojson
from services.water_quality_repo import get_water_quality

logger = logging.getLogger(__name__)

GIOSPATIAL_GREEN = "#265B01"
GIOSPATIAL_DARK_GREEN = "#152C00"
GIOSPATIAL_NAVY = "#141B44"
GIOSPATIAL_GREEN_BRIGHT = "#5BC221"  # readable on dark backgrounds; header/chart accent only


def render_header() -> None:
    st.markdown(
        f"""
        <div style="background-color:{GIOSPATIAL_NAVY}; padding: 1rem 1.5rem;
                    border-radius: 6px; margin-bottom: 1rem;
                    border: 1px solid rgba(255,255,255,0.08);">
            <h2 style="color:white; margin:0; font-family:'Montserrat', sans-serif;">
                KMFRI Papyrus Wetland M&amp;E Platform
            </h2>
            <p style="color:{GIOSPATIAL_GREEN_BRIGHT}; margin:0; font-family:'Montserrat', sans-serif;">
                Lake Naivasha Basin · GIOSPATIAL
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_panel() -> None:
    sites_fc = get_nursery_sites_geojson()
    polygons_fc = get_restoration_polygons_geojson()

    component_value = naivasha_map(
        nursery_sites=sites_fc,
        restoration_polygons=polygons_fc,
        selected_site_id=get_selected_site_id(),
        key="naivasha_map_main",
    )
    sync_from_map_component(component_value)


def render_kpi_row(site_id: int | None) -> None:
    cols = st.columns(3)
    site = get_nursery_site_by_id(site_id) if site_id else None

    with cols[0]:
        st.metric("Selected site", site["site_name"] if site else "All sites")
    with cols[1]:
        st.metric("Stakeholder", site["stakeholder"] if site else "—")
    with cols[2]:
        st.metric("Nursery capacity", site.get("capacity_units", "—") if site else "—")


def render_charts_panel(site_id: int | None) -> None:
    landings = get_landings(site_id)
    water_quality = get_water_quality(site_id)
    polygons_fc = get_restoration_polygons_geojson()

    st.plotly_chart(charts.landings_trend(landings), use_container_width=True)
    st.plotly_chart(charts.water_quality_trend(water_quality), use_container_width=True)
    st.plotly_chart(charts.cover_progress(polygons_fc), use_container_width=True)


def render_page() -> None:
    render_header()
    map_col, chart_col = st.columns([3, 2])

    with map_col:
        render_map_panel()

    site_id = get_selected_site_id()

    with chart_col:
        render_kpi_row(site_id)
        render_charts_panel(site_id)
