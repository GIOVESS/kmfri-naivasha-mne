"""Plotly figures for the M&E dashboard. Pure functions: data in, figure out."""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


def landings_trend(landings: list[dict[str, Any]]) -> go.Figure:
    fig = go.Figure()
    if not landings:
        fig.update_layout(title="Fish landings — no data for current filter")
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
        fig.update_layout(title="Water quality — no data for current filter")
        return fig

    readings = sorted(readings, key=lambda r: r["sample_date"])
    dates = [r["sample_date"] for r in readings]

    fig.add_trace(go.Scatter(x=dates, y=[r["turbidity_ntu"] for r in readings],
                              mode="lines+markers", name="Turbidity (NTU)"))
    fig.add_trace(go.Scatter(x=dates, y=[r["dissolved_o2_mgl"] for r in readings],
                              mode="lines+markers", name="Dissolved O2 (mg/L)", yaxis="y2"))

    fig.update_layout(
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
        fig.update_layout(title="Papyrus cover progress — no data")
        return fig

    labels = [f["properties"]["polygon_code"] for f in features]
    covers = [f["properties"].get("cover_pct") or 0 for f in features]
    phases = [f["properties"]["phase"] for f in features]

    phase_colors = {"pilot": "#265B01", "target": "#152C00", "baseline": "#8a8a8a"}
    colors = [phase_colors.get(p, "#265B01") for p in phases]

    fig.add_trace(go.Bar(x=labels, y=covers, marker_color=colors, text=phases))
    fig.update_layout(
        title="Papyrus cover progress by restoration polygon (%)",
        xaxis_title="Polygon",
        yaxis_title="Cover %",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig
