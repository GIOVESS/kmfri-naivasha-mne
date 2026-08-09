"""
Page structure: network KPI row, then map + selection-detail panel side by
side (map ~2/3 width, detail panel ~1/3 — see render_map_and_selection),
then a 2-column chart grid, then the restoration-vs-fisheries feature chart,
then summary tables. Nav controls for the map live in the component itself
(components/naivasha_map/frontend/src/main.js).

Site filter is synced from map clicks via dashboard.filters. On narrow
screens Streamlit's own column-wrapping stacks the map/detail panel and
chart pairs vertically — no separate mobile layout branch needed.
"""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from components.naivasha_map import naivasha_map
from dashboard import charts
from dashboard.filters import get_selected_site_id, get_reset_token, sync_from_map_component, trigger_reset
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
    # clamp() instead of a fixed size/padding + media query breakpoint — scales
    # smoothly from phone widths up to desktop without a hard jump at any
    # particular viewport size.
    st.markdown(
        f"""
        <div style="background-color:{GIOSPATIAL_NAVY};
                    padding: clamp(0.75rem, 3vw, 1rem) clamp(1rem, 4vw, 1.5rem);
                    border-radius: 6px; margin-bottom: 1rem;
                    border: 1px solid rgba(255,255,255,0.08);">
            <h2 style="color:white; margin:0; font-family:'Montserrat', sans-serif;
                       font-size: clamp(1.25rem, 4vw, 1.75rem);">
                KMFRI Papyrus Wetland M&amp;E Platform
            </h2>
            <p style="color:{GIOSPATIAL_GREEN_BRIGHT}; margin:0; font-family:'Montserrat', sans-serif;
                      font-size: clamp(0.85rem, 2.5vw, 1rem);">
                Lake Naivasha Basin · GIOSPATIAL
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_and_selection(site_id: int | None, sites: list[dict]) -> None:
    """
    Map (left, ~2/3 width) and the selection detail panel (right, ~1/3) side
    by side — on a full desktop-width page, stacking these vertically (map
    full-width, then a KPI row below) left a lot of horizontal space unused.
    The panel includes the Reset filters control, since it acts directly on
    what's shown in the map to its left.
    """
    map_col, detail_col = st.columns([2, 1], gap="medium")

    with map_col:
        sites_fc = get_nursery_sites_geojson()
        polygons_fc = get_restoration_polygons_geojson()
        component_value = naivasha_map(
            nursery_sites=sites_fc,
            restoration_polygons=polygons_fc,
            selected_site_id=site_id,
            reset_token=get_reset_token(),
            height=560,
            key="naivasha_map_main",
        )
        sync_from_map_component(component_value)
        st.caption(
            "Basemap: CARTO Voyager (free tiles). Click a marker to filter the "
            "charts below to that site; use Home (top-left) to reset the view."
        )

    with detail_col:
        header_col, reset_col = st.columns([2, 1])
        with header_col:
            st.caption("Site filter")
        with reset_col:
            if st.button("Reset", use_container_width=True, disabled=site_id is None):
                trigger_reset()
                st.rerun()

        site = get_nursery_site_by_id(site_id) if site_id else None
        total_capacity = sum((s.get("capacity_units") or 0) for s in sites)

        # Stacked rather than in columns — a 1/3-width panel is too narrow
        # for 4 side-by-side st.metric cards without them wrapping awkwardly.
        st.metric("Selected site", site["site_name"] if site else "All sites")
        st.metric("Stakeholder", site["stakeholder"] if site else f"{len(sites)} sites")
        st.metric("Nursery capacity", site.get("capacity_units", "—") if site else f"{total_capacity:,}")
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

    # Paired as two capacity/comparison bar charts, rather than leaving
    # stakeholder_capacity by itself full-width on its own row below.
    row2_left, row2_right = st.columns(2)
    with row2_left:
        st.plotly_chart(charts.cover_progress(polygons_fc), use_container_width=True)
    with row2_right:
        # Network-wide, not filtered by site selection — deliberately paired
        # here rather than filtered, since it's a basin-level comparison.
        st.plotly_chart(charts.stakeholder_capacity(sites), use_container_width=True)

    # species_share is a compact donut; pairing it with a plain chart would
    # leave one side visually heavier, so the second column is a short
    # callout instead — fills the space without competing for attention.
    row3_left, row3_right = st.columns(2)
    with row3_left:
        st.plotly_chart(charts.species_share(landings), use_container_width=True)
    with row3_right:
        totals: dict[str, float] = {}
        for r in landings:
            totals[r["species"]] = totals.get(r["species"], 0) + r["catch_kg"]
        if totals:
            leading_species, leading_kg = max(totals.items(), key=lambda kv: kv[1])
            share_pct = leading_kg / sum(totals.values()) * 100
            st.metric("Leading species", leading_species, f"{share_pct:.0f}% of catch")
            st.caption(
                "Based on the current site filter." if site_id else "Basin-wide, all sites."
            )
        else:
            st.caption("No catch data for the current filter.")


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

    site_id = get_selected_site_id()
    render_map_and_selection(site_id, sites)
    st.divider()

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
