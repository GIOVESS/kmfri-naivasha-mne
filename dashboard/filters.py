"""Shared filter state, synchronized with the map component's click output."""
from __future__ import annotations

import streamlit as st

SITE_ID_KEY = "selected_site_id"
LAST_CLICK_SEQ_KEY = "_map_last_click_seq"


def get_selected_site_id() -> int | None:
    return st.session_state.get(SITE_ID_KEY)


def set_selected_site_id(site_id: int | None) -> None:
    st.session_state[SITE_ID_KEY] = site_id


def sync_from_map_component(component_value: dict | None) -> None:
    """
    component_value is whatever bridge.js passes via Streamlit.setComponentValue.

    Streamlit component functions keep returning the same payload on every
    script rerun until the frontend calls setComponentValue again — they
    don't clear just because Python passed a different prop in. Without the
    click_seq check below, a Reset Filters click (a pure Python-side change
    to session_state) would immediately get overwritten right back to the
    previously-clicked site on the very next read of this stale payload,
    since site_id != None would always look like "a new selection" even
    when it's really just the same old click being replayed.
    """
    if not component_value:
        return

    click_seq = component_value.get("click_seq")
    if click_seq is None or click_seq == st.session_state.get(LAST_CLICK_SEQ_KEY):
        return  # no new click since we last processed one — nothing to do

    st.session_state[LAST_CLICK_SEQ_KEY] = click_seq
    set_selected_site_id(component_value.get("site_id"))
