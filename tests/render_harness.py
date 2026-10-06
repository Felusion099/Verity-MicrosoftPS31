"""TEST-ONLY entrypoint: renders a page by query param (?page=overview&role=...).

Used by the automated test suite for per-page coverage, because AppTest
cannot click st.navigation's sidebar widget. Not part of the production app.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from src import config, data_loader, filters
from src.context import build_context
from pages import overview, revenue, products, regions, customers, data_quality, governance, ai_trainer

RENDERERS = {
    "overview": overview.render,
    "revenue": revenue.render,
    "products": products.render,
    "regions": regions.render,
    "customers": customers.render,
    "data_quality": data_quality.render,
    "ai_trainer": ai_trainer.render,
    "governance": governance.render,
}

st.set_page_config(page_title="Harness", layout="wide")

enriched = data_loader.load_enriched()
role = st.query_params.get("role", config.DEFAULT_ROLE)
if role not in config.ROLES:
    role = config.DEFAULT_ROLE

# default filter state matching the app's first impression (current year)
if "years" not in st.session_state:
    st.session_state.years = [int(enriched["Year"].max())]
spec = filters.FilterSpec(years=st.session_state.years)
ctx = build_context(enriched, role, spec)

page = st.query_params.get("page", "overview")
RENDERERS.get(page, overview.render)(ctx)
