"""Plotly figures for the M&E dashboard. Pure functions: data in, figure out."""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

# Dark-mode chart chrome, applied via fig.update_layout(**DARK_LAYOUT) in every
# figure below so charts match the app's dark Streamlit theme instead of
# rendering as bright white cards.
DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#141B24",
    plot_bgcolor="#141B24",
    font=dict(color="#E8ECE4"),
)


def landings_trend(landings: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    if not landings:
        fig.update_layout(title="Fish landings — no data for current filter", **DARK_LAYOUT)
        return fig

    by_species: dict[str, list[dict[str, Any]]] = {}
    for row in landings:
        by_species.setdefault(row["species"], []).append(row)

    for species, rows in by_species.items():
        rows = sorted(rows, key=lambda r: r["landing_date"])
        fig.add_trace(
            go.Scatter(
                x=[r["landing_date"] for r in rows],
                y=[r["catch_kg"] for r in rows],
                mode="lines+markers",
                name=species,
            )
        )
    fig.update_layout(
        **DARK_LAYOUT,
        title="Fish landings over time (kg)",
        xaxis_title="Date",
        yaxis_title="Catch (kg)",
        legend_title="Species",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def water_quality_trend(readings: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    if not readings:
        fig.update_layout(title="Water quality — no data for current filter", **DARK_LAYOUT)
        return fig

    readings = sorted(readings, key=lambda r: r["sample_date"])
    dates = [r["sample_date"] for r in readings]

    fig.add_trace(go.Scatter(x=dates, y=[r["turbidity_ntu"] for r in readings],
                              mode="lines+markers", name="Turbidity (NTU)"))
    fig.add_trace(go.Scatter(x=dates, y=[r["dissolved_o2_mgl"] for r in readings],
                              mode="lines+markers", name="Dissolved O2 (mg/L)", yaxis="y2"))

    fig.update_layout(
        **DARK_LAYOUT,
        title="Water quality over time",
        xaxis_title="Date",
        yaxis=dict(title="Turbidity (NTU)"),
        yaxis2=dict(title="Dissolved O2 (mg/L)", overlaying="y", side="right"),
        legend_title="Metric",
        margin=dict(l=40, r=40, t=40, b=40),
    )
    return fig


def cover_progress(polygons_geojson: dict[str, Any]) -> go.Figure:
    """Bar chart of papyrus cover % per restoration polygon, grouped by phase."""
    features = polygons_geojson.get("features", [])
    fig = go.Figure()
    if not features:
        fig.update_layout(title="Papyrus cover progress — no data", **DARK_LAYOUT)
        return fig

    labels = [f["properties"]["polygon_code"] for f in features]
    covers = [f["properties"].get("cover_pct") or 0 for f in features]
    phases = [f["properties"]["phase"] for f in features]

    # Brightened for contrast against the dark chart background — the brand's
    # dark green (#152C00) is nearly invisible on #141B24, so "target" uses a
    # lighter tint instead of the literal brand color here.
    phase_colors = {"pilot": "#3A8A00", "target": "#8FD14F", "baseline": "#9BA3AE"}
    colors = [phase_colors.get(p, "#3A8A00") for p in phases]

    fig.add_trace(go.Bar(x=labels, y=covers, marker_color=colors, text=phases))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Papyrus cover progress by restoration polygon (%)",
        xaxis_title="Polygon",
        yaxis_title="Cover %",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


def species_share(landings: list[dict[str, Any]]) -> go.Figure:
    """Donut: total catch_kg share by species, for the current site filter."""
    totals: dict[str, float] = {}
    for row in landings:
        totals[row["species"]] = totals.get(row["species"], 0) + row["catch_kg"]

    fig = go.Figure()
    if not totals:
        fig.update_layout(title="Catch share by species — no data", **DARK_LAYOUT)
        return fig

    species_colors = {"Tilapia": "#5BC221", "Common carp": "#E8664B"}
    colors = [species_colors.get(s, "#9BA3AE") for s in totals]

    fig.add_trace(go.Pie(labels=list(totals.keys()), values=list(totals.values()),
                          hole=0.5, marker=dict(colors=colors)))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Total catch share by species (kg)",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def stakeholder_capacity(sites: list[dict[str, Any]]) -> go.Figure:
    """Bar: total nursery seedling capacity summed by stakeholder, network-wide."""
    totals: dict[str, int] = {}
    for s in sites:
        totals[s["stakeholder"]] = totals.get(s["stakeholder"], 0) + (s.get("capacity_units") or 0)

    fig = go.Figure()
    if not totals:
        fig.update_layout(title="Nursery capacity by stakeholder — no data", **DARK_LAYOUT)
        return fig

    fig.add_trace(go.Bar(x=list(totals.keys()), y=list(totals.values()), marker_color="#3A8A00"))
    fig.update_layout(
        **DARK_LAYOUT,
        title="Nursery capacity by stakeholder (seedlings)",
        xaxis_title="Stakeholder",
        yaxis_title="Capacity (units)",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig
