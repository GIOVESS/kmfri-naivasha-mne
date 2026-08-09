"""
Page structure: full-width map up top (nav controls live in the component
itself — see components/naivasha_map/frontend/src/main.js), KPI rows above
and below it, then a 2-column grid of charts, then a full sites table.

Site filter is synced from map clicks via dashboard.filters.
"""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from components.naivasha_map import naivasha_map
from dashboard import charts
from dashboard.filters import get_selected_site_id, set_selected_site_id, sync_from_map_component
from services.landings_repo import get_landings
from services.sites_repo import get_nursery_site_by_id, get_nursery_sites_geojson, \
    get_restoration_polygons_geojson, list_nursery_sites
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
        height=560,
        key="naivasha_map_main",
    )
    sync_from_map_component(component_value)
    st.caption(
        "Basemap: CARTO Voyager (free tiles). Click a marker to filter the "
        "charts below to that site; use Home (top-left) to reset the view."
    )


def render_top_kpi_row(site_id: int | None, sites: list[dict]) -> None:
    """Selection-aware row: what you're currently looking at, plus a control
    to clear the site filter and return to the all-sites view."""
    site = get_nursery_site_by_id(site_id) if site_id else None
    total_capacity = sum((s.get("capacity_units") or 0) for s in sites)

    header_col, reset_col = st.columns([5, 1])
    with header_col:
        st.caption("Site filter")
    with reset_col:
        if st.button("Reset filters", use_container_width=True, disabled=site_id is None):
            set_selected_site_id(None)
            st.rerun()

    cols = st.columns(4)
    with cols[0]:
        st.metric("Selected site", site["site_name"] if site else "All sites")
    with cols[1]:
        st.metric("Stakeholder", site["stakeholder"] if site else f"{len(sites)} sites")
    with cols[2]:
        st.metric("Nursery capacity", site.get("capacity_units", "—") if site else f"{total_capacity:,}")
    with cols[3]:
        st.metric("Established", site.get("established", "—") if site else "—")


def render_network_kpi_row(
    sites: list[dict], all_landings: list[dict], all_wq: list[dict], polygons_fc: dict
) -> None:
    """Selection-independent row: basin-wide totals, always visible."""
    total_catch = sum(r["catch_kg"] for r in all_landings)
    latest_wq = max(all_wq, key=lambda r: r["sample_date"]) if all_wq else None
    features = polygons_fc.get("features", [])
    avg_cover = (
        sum((f["properties"].get("cover_pct") or 0) for f in features) / len(features)
        if features else None
    )

    cols = st.columns(4)
    with cols[0]:
        st.metric("Restoration polygons", len(features))
    with cols[1]:
        st.metric("Avg. papyrus cover", f"{avg_cover:.1f}%" if avg_cover is not None else "—")
    with cols[2]:
        st.metric("Total catch (all-time)", f"{total_catch:,.0f} kg" if total_catch else "—")
    with cols[3]:
        st.metric(
            "Latest water sample",
            latest_wq["sample_date"] if latest_wq else "—",
            help="Most recent turbidity/DO/pH/temperature reading across all sites.",
        )


def render_charts_grid(
    site_id: int | None,
    landings: list[dict],
    water_quality: list[dict],
    polygons_fc: dict,
    sites: list[dict],
) -> None:
    row1_left, row1_right = st.columns(2)
    with row1_left:
        st.plotly_chart(charts.landings_trend(landings), use_container_width=True)
    with row1_right:
        st.plotly_chart(charts.water_quality_trend(water_quality), use_container_width=True)

    row2_left, row2_right = st.columns(2)
    with row2_left:
        st.plotly_chart(charts.cover_progress(polygons_fc), use_container_width=True)
    with row2_right:
        st.plotly_chart(charts.species_share(landings), use_container_width=True)

    # Network-wide, not filtered by site selection — deliberately full-width
    # since it's a basin-level comparison, not a per-site drill-down.
    st.plotly_chart(charts.stakeholder_capacity(sites), use_container_width=True)


def render_sites_table(sites: list[dict]) -> None:
    st.subheader("Nursery sites")
    if not sites:
        st.caption("No nursery sites found.")
        return
    df = pd.DataFrame(sites)[["site_code", "site_name", "stakeholder", "capacity_units"]]
    df.columns = ["Site code", "Name", "Stakeholder", "Capacity (seedlings)"]
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_water_quality_summary(sites: list[dict], all_wq: list[dict]) -> None:
    st.subheader("Water quality summary by site")
    if not all_wq:
        st.caption("No water quality samples found.")
        return
    site_name_by_id = {s["id"]: s["site_name"] for s in sites}
    df = pd.DataFrame(all_wq)
    df["site_name"] = df["site_id"].map(site_name_by_id)
    summary = (
        df.groupby("site_name")[["turbidity_ntu", "ph", "dissolved_o2_mgl", "temp_c"]]
        .mean()
        .round(2)
        .reset_index()
    )
    summary.columns = ["Site", "Avg turbidity (NTU)", "Avg pH", "Avg dissolved O2 (mg/L)", "Avg temp (°C)"]
    st.dataframe(summary, use_container_width=True, hide_index=True)


def render_page() -> None:
    render_header()

    sites = list_nursery_sites()
    polygons_fc = get_restoration_polygons_geojson()
    all_landings = get_landings()
    all_wq = get_water_quality()

    render_network_kpi_row(sites, all_landings, all_wq, polygons_fc)
    st.divider()

    render_map_panel()

    site_id = get_selected_site_id()
    st.divider()
    render_top_kpi_row(site_id, sites)

    landings = get_landings(site_id) if site_id else all_landings
    water_quality = get_water_quality(site_id) if site_id else all_wq

    render_charts_grid(site_id, landings, water_quality, polygons_fc, sites)
    st.divider()

    st.subheader("Does restoration progress track with fisheries recovery?")
    st.caption(
        "Basin-wide, not filtered by the map selection above — this is the "
        "core relationship KMFRI/WWF are monitoring across the whole platform."
    )
    st.plotly_chart(charts.landings_vs_cover(all_landings, polygons_fc), use_container_width=True)
    st.divider()

    render_water_quality_summary(sites, all_wq)
    st.divider()
    render_sites_table(sites)
