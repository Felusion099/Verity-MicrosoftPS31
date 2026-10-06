"""Verity — application shell.

Header, sidebar navigation, demo RBAC role selector, global filters, active
filter chips, export and page dispatch. Pages live in pages/ and receive a
shared context (filtered data, previous period, role, ...).
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# make src/ imports work regardless of the working directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from src import config, data_loader, filters, insights, rls
from src.context import build_context
from src.formatting import format_datetime, format_int
from pages import overview, revenue, products, regions, customers, data_quality, governance, ai_trainer

st.set_page_config(page_title=config.APP_NAME, layout="wide",
                   initial_sidebar_state="expanded")

# --------------------------------------------------------------------------
# CSS — enterprise dark theme (cards, chips, header, sidebar)
# --------------------------------------------------------------------------
CSS = """
<style>
:root {
  --bg: #0b1220; --panel: #111a2e; --panel-2: #0e1626; --border: #1d2a44;
  --text: #e6edf7; --muted: #8fa3bf; --primary: #3b82f6;
  --green: #34d399; --red: #f87171; --amber: #fbbf24;
}
html, body, [data-testid="stAppViewContainer"] { background: var(--bg); }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
.block-container { padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1400px; }

.app-header { display: flex; justify-content: space-between; align-items: center;
  background: linear-gradient(90deg, #0e1729, #111a2e); border: 1px solid var(--border);
  border-radius: 14px; padding: 14px 20px; margin-bottom: 0.4rem; }
.app-header .logo { font-size: 1.25rem; font-weight: 800; color: var(--text); letter-spacing: -0.02em; }
.app-header .logo .accent { color: var(--primary); }
.app-header .tag { font-size: 0.78rem; color: var(--muted); }
.app-header .status { font-size: 0.76rem; color: var(--muted); text-align: right; }
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: var(--green); margin-right: 6px; box-shadow: 0 0 6px rgba(52,211,153,0.8); }

.page-title { font-size: 1.5rem; font-weight: 700; letter-spacing: -0.02em; color: var(--text); margin-bottom: 0.05rem; }
.page-subtitle { font-size: 0.9rem; color: var(--muted); margin-bottom: 1rem; }

.kpi-card { background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
  padding: 15px 18px 11px; height: 100%; }
.kpi-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); font-weight: 600; }
.kpi-value { font-size: 1.55rem; font-weight: 700; color: var(--text); margin: 4px 0 2px; letter-spacing: -0.02em; }
.kpi-delta { font-size: 0.8rem; font-weight: 600; }
.delta-up { color: var(--green); } .delta-down { color: var(--red); } .delta-flat { color: var(--muted); }
.kpi-sub { font-size: 0.72rem; color: var(--muted); }
.kpi-spark { margin-top: 6px; }

.chip-row { display: flex; flex-wrap: wrap; gap: 6px; margin: 0.45rem 0 0.9rem; align-items: center; }
.chip { background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.35); color: #bfdbfe;
  border-radius: 999px; padding: 2px 10px; font-size: 0.74rem; font-weight: 500; }
.chip-muted { background: rgba(148,163,184,0.08); border-color: rgba(148,163,184,0.25); color: var(--muted); }

.badge-cert { display: inline-block; background: rgba(52,211,153,0.14); color: var(--green);
  border: 1px solid rgba(52,211,153,0.4); border-radius: 999px; font-size: 0.72rem;
  font-weight: 700; padding: 2px 10px; letter-spacing: 0.04em; }
.badge-warn { display: inline-block; background: rgba(251,191,36,0.12); color: var(--amber);
  border: 1px solid rgba(251,191,36,0.4); border-radius: 999px; font-size: 0.72rem;
  font-weight: 700; padding: 2px 10px; letter-spacing: 0.04em; }
.badge-danger { display: inline-block; background: rgba(248,113,113,0.12); color: var(--red);
  border: 1px solid rgba(248,113,113,0.4); border-radius: 999px; font-size: 0.72rem;
  font-weight: 700; padding: 2px 10px; letter-spacing: 0.04em; }

.metric-hero { background: linear-gradient(135deg, #101d36, #0f1a30); border: 1px solid #23406e;
  border-radius: 16px; padding: 22px 24px; }
.metric-hero .kpi-value { font-size: 2rem; }
.hero-formula { font-size: 1.05rem; color: #93c5fd; font-weight: 600; margin: 4px 0 8px; }

.flow-box { background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
  padding: 12px 14px; text-align: center; }
.flow-result { border-color: #23406e; background: linear-gradient(135deg, #101d36, #0f1a30); }
.flow-val { font-size: 1.05rem; font-weight: 700; color: var(--text); }
.flow-op { color: var(--muted); font-size: 1.5rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; height: 100%; }

.insight-item { background: var(--panel); border: 1px solid var(--border);
  border-left: 3px solid var(--primary); border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }
.alert-positive { border-left-color: var(--green); }
.alert-negative { border-left-color: var(--red); }
.alert-warning { border-left-color: var(--amber); }
.alert-neutral { border-left-color: var(--primary); }
.insight-title { font-size: 0.86rem; font-weight: 700; color: var(--text); margin-bottom: 3px; }
.insight-text { font-size: 0.8rem; color: var(--muted); line-height: 1.45; }
.dq-row { display: flex; justify-content: space-between; align-items: center; }
.dq-name { font-size: 0.86rem; font-weight: 600; color: var(--text); }

.target-row { background: var(--panel); border: 1px solid var(--border); border-radius: 14px;
  padding: 14px 16px; height: 100%; }
.target-head { display: flex; justify-content: space-between; font-size: 0.8rem;
  font-weight: 700; color: var(--text); margin-bottom: 8px; }
.target-bar { height: 8px; background: rgba(148,163,184,0.12); border-radius: 999px; overflow: hidden; }
.target-fill { height: 100%; border-radius: 999px; }
.target-sub { font-size: 0.72rem; color: var(--muted); margin-top: 8px; }

.empty-state { background: var(--panel); border: 1px dashed var(--border); border-radius: 14px;
  padding: 40px 20px; text-align: center; }
.empty-title { font-size: 1rem; font-weight: 700; color: var(--text); }
.empty-hint { font-size: 0.84rem; color: var(--muted); margin-top: 6px; }

[data-testid="stSidebar"] { background: var(--panel-2); border-right: 1px solid var(--border); }
div[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom-color: var(--border); }
.stTabs [data-baseweb="tab"] { background: transparent; color: var(--muted); border-radius: 8px 8px 0 0; padding: 6px 14px; }
.stTabs [aria-selected="true"] { color: var(--text); background: rgba(59,130,246,0.12); }
div[data-baseweb="radio"] label { margin-bottom: 0; }
</style>
"""

# --------------------------------------------------------------------------
# Data + session state
# --------------------------------------------------------------------------
build_info = data_loader.ensure_database()
enriched = data_loader.load_enriched()

if "role" not in st.session_state:
    st.session_state.role = config.DEFAULT_ROLE
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = datetime.now()

st.markdown(CSS, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
records = f"{len(enriched):,} records"
st.markdown(
    '<div class="app-header">'
    '<div><div class="logo">Ver<span class="accent">ity</span></div>'
    f'<div class="tag">{config.APP_SUBTITLE} · {config.APP_TAGLINE}</div></div>'
    '<div class="status">'
    '<div><span class="status-dot"></span><b>Data Fresh</b></div>'
    f'<div>Last refresh: {format_datetime(st.session_state.last_refresh)}</div>'
    f'<div>{records} · governed model</div>'
    '</div></div>',
    unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Sidebar: RBAC, filters, export, refresh
# (the page navigation renders automatically at the top of the sidebar)
# --------------------------------------------------------------------------
with st.sidebar:
    role = st.selectbox("User Role (Demo RBAC)", list(config.ROLES), key="role")
    st.caption(config.ROLES[role]["label"])

    st.divider()
    spec = filters.render_sidebar_filters(enriched)

    st.divider()
    with st.expander("Export"):
        # export must respect current filters AND the demo role scope
        _rls_view = rls.apply_rls(enriched, role)
        _export_view = filters.apply_filters(_rls_view, spec)
        if len(_export_view):
            csv_bytes = _export_view.to_csv(index=False).encode("utf-8")
            st.download_button("Filtered transactions (CSV)", csv_bytes,
                               file_name=f"verity_export_{datetime.now():%Y%m%d}.csv",
                               mime="text/csv", width="stretch")
            md_bytes = insights.executive_summary_md(
                _export_view, filters.apply_filters(_rls_view, filters.previous_period_spec(spec, _export_view))
                if filters.previous_period_spec(spec, _export_view) else None).encode("utf-8")
            st.download_button("Executive summary (Markdown)", md_bytes,
                               file_name=f"verity_summary_{datetime.now():%Y%m%d}.md",
                               mime="text/markdown", width="stretch")
        else:
            st.caption("No data in scope to export.")

    st.divider()
    if st.button("↻ Local Data Refresh", width="stretch",
                 help="Demo refresh — reloads the local analytical model. "
                      "Honest architecture: not a real-time feed."):
        data_loader.refresh_data()
        st.session_state.last_refresh = datetime.now()
        st.rerun()
    st.caption("Deterministic local model · no cloud, no live feed.")

# --------------------------------------------------------------------------
# Apply RBAC + filters, build page context (shared builder)
# --------------------------------------------------------------------------
ctx = build_context(enriched, role, spec)
ctx["build_info"] = build_info
st.session_state.ctx = ctx

# active filter chips + RBAC banner
rbac_label = (f"Demo RBAC: {' · '.join(rls.allowed_regions(role))}"
              if rls.is_restricted(role) else None)
chip_html = ('<div class="chip-row">'
             '<span class="chip chip-muted">Filters applied</span>'
             + "".join(f'<span class="chip">{c}</span>' for c in filters.active_filter_chips(spec))
             + (f'<span class="chip chip-muted">{rbac_label}</span>' if rbac_label else "")
             + '</div>')
st.markdown(chip_html, unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Page dispatch — st.navigation gives REAL URL routes:
# /overview, /revenue, /products, /regions, /customers, /data_quality,
# /ai_trainer, /governance (the entrypoint file is the router/frame).
# Errors are shown cleanly, never as stack traces.
# --------------------------------------------------------------------------
page_defs = [
    st.Page(lambda: overview.render(st.session_state.ctx), title="Overview",
            url_path="overview", default=True),
    st.Page(lambda: revenue.render(st.session_state.ctx), title="Revenue", url_path="revenue"),
    st.Page(lambda: products.render(st.session_state.ctx), title="Products", url_path="products"),
    st.Page(lambda: regions.render(st.session_state.ctx), title="Regions", url_path="regions"),
    st.Page(lambda: customers.render(st.session_state.ctx), title="Customers", url_path="customers"),
    st.Page(lambda: data_quality.render(st.session_state.ctx), title="Data Quality",
            url_path="data_quality"),
    st.Page(lambda: ai_trainer.render(st.session_state.ctx), title="AI Trainer", url_path="ai_trainer"),
    st.Page(lambda: governance.render(st.session_state.ctx), title="Metric Governance",
            url_path="governance"),
]

try:
    pg = st.navigation(page_defs, position="sidebar", expanded=True)
    pg.run()
except Exception as exc:  # noqa: BLE001 — surface a clean message to the user
    print(f"[Verity] {type(exc).__name__}: {exc}", file=sys.stderr)
    st.error("Something went wrong rendering this page. "
             "Try resetting the filters — the issue has been logged.")

st.markdown("")
st.markdown(
    f'<div style="text-align:center; color: var(--muted); font-size: 0.74rem; padding: 10px 0 0;">'
    f'{config.APP_NAME} · {config.PS_ID} · Bennett Microsoft Innovate 2026 · '
    f'One Definition. One Number. One Truth.</div>',
    unsafe_allow_html=True)
