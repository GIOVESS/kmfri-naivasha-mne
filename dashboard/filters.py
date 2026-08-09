"""Shared filter state, synchronized with the map component's click output."""
from __future__ import annotations

import streamlit as st

SITE_ID_KEY = "selected_site_id"
LAST_CLICK_SEQ_KEY = "_map_last_click_seq"
RESET_TOKEN_KEY = "_map_reset_token"


def get_selected_site_id() -> int | None:
    return st.session_state.get(SITE_ID_KEY)


def set_selected_site_id(site_id: int | None) -> None:
    st.session_state[SITE_ID_KEY] = site_id


def get_reset_token() -> int:
    return st.session_state.get(RESET_TOKEN_KEY, 0)


def trigger_reset() -> None:
    """
    Clears the site filter for this render AND bumps a reset token that's
    passed down to the map component as a prop (naivasha_map(reset_token=...)
    in layout.py). The component reacts to that token changing by explicitly
    re-emitting {site_id: None} itself, through the exact same channel used
    for marker clicks (Streamlit.setComponentValue — see main.js).

    That's the point: previously there were two independent writers to
    session_state's site-id key — this function, and sync_from_map_component
    reading the map component's sticky return value (Streamlit component
    functions keep returning the same payload across reruns until the
    frontend calls setComponentValue again). Two writers racing against
    Streamlit's exact rerun order is exactly the kind of setup where one
    write silently clobbers the other. Routing the reset through the map
    component too, so it becomes the sole source of truth for site_id,
    removes that race rather than trying to out-guess the rerun timing.
    """
    set_selected_site_id(None)
    st.session_state[RESET_TOKEN_KEY] = get_reset_token() + 1


def sync_from_map_component(component_value: dict | None) -> None:
    """
    component_value is whatever bridge.js passes via Streamlit.setComponentValue.
    This is the only place that writes SITE_ID_KEY from the map's output,
    keyed on click_seq so a stale/replayed payload (which Streamlit keeps
    returning until the frontend calls setComponentValue again) only ever
    gets applied once, whether it came from a marker click or from the
    frontend's own reset-token-triggered re-emission.
    """
    if not component_value:
        return

    click_seq = component_value.get("click_seq")
    last_seq = st.session_state.get(LAST_CLICK_SEQ_KEY)
    if click_seq is None or (last_seq is not None and click_seq <= last_seq):
        return  # already processed this (or an older) payload — nothing new to apply

    st.session_state[LAST_CLICK_SEQ_KEY] = click_seq
    set_selected_site_id(component_value.get("site_id"))
