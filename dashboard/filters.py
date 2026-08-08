"""Shared filter state, synchronized with the map component's click output."""
from __future__ import annotations

import streamlit as st

SITE_ID_KEY = "selected_site_id"


def get_selected_site_id() -> int | None:
    return st.session_state.get(SITE_ID_KEY)


def set_selected_site_id(site_id: int | None) -> None:
    st.session_state[SITE_ID_KEY] = site_id


def sync_from_map_component(component_value: dict | None) -> None:
    """component_value is whatever bridge.js passes via Streamlit.setComponentValue."""
    if not component_value:
        return
    site_id = component_value.get("site_id")
    if site_id is not None and site_id != get_selected_site_id():
        set_selected_site_id(site_id)
