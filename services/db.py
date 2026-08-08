"""
Supabase client singleton.

Uses PostgREST (via supabase-py) for CRUD and Postgres RPC functions
(defined in scripts/schema.sql) for geometry-bearing reads, so the app
never needs a raw psycopg2/libpq connection string.
"""
from __future__ import annotations

import logging
from functools import lru_cache

import streamlit as st
from supabase import Client, create_client

logger = logging.getLogger(__name__)


class SupabaseConfigError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_client() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
    except KeyError as exc:
        raise SupabaseConfigError(
            "Missing [supabase] url/anon_key in .streamlit/secrets.toml"
        ) from exc

    try:
        client = create_client(url, key)
    except Exception:
        logger.exception("Failed to initialize Supabase client")
        raise

    return client


def call_rpc(fn_name: str, params: dict | None = None) -> dict:
    """Call a Postgres RPC function, returning its JSON result. Raises on error."""
    client = get_client()
    try:
        resp = client.rpc(fn_name, params or {}).execute()
    except Exception:
        logger.exception("RPC call failed: %s", fn_name)
        raise
    return resp.data
