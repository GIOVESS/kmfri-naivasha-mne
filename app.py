"""
KMFRI Papyrus Wetland M&E Platform — Streamlit entrypoint.

Layout, data access, and chart logic live in dashboard/ and services/;
this file only wires page config and calls dashboard.layout.render_page().
"""
import streamlit as st

from dashboard.layout import render_page

st.set_page_config(
    page_title="KMFRI Papyrus Wetland M&E — GIOSPATIAL",
    page_icon="🌿",
    layout="wide",
)

render_page()
