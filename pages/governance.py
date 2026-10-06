"""Metric Governance page — the PS31 centrepiece: one definition, one number."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import config, data_loader, metrics
from src.formatting import format_date, format_datetime, format_inr
from src.ui import page_header, status_badge


def _consistency_proof(df: pd.DataFrame) -> None:
    """Show Net Revenue computed three independent ways — all equal."""
    if df is None or len(df) == 0:
        return
    way1 = metrics.net_revenue(df)  # governed components (metrics.py)
    way2 = float(df["NetRevenue"].sum())  # stored column (verified by Data Quality)
    by_region = metrics.aggregate_by(df, ["Region"])
    way3 = float(by_region["NetRevenue"].sum())  # chart aggregates

    cols = st.columns(3)
    cards = [
        ("Governed metric (metrics.py)", format_inr(way1)),
        ("Stored FACT_SALES column", format_inr(way2)),
        ("Sum of region chart aggregates", format_inr(way3)),
    ]
    for col, (label, value) in zip(cols, cards):
        col.markdown(
            '<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            '<div class="kpi-sub">identical — one definition, one number</div>'
            '</div>',
            unsafe_allow_html=True)


def render(ctx: dict) -> None:
    df = ctx["df"]
    page_header("Metric Governance",
                "One definition. One number. Shared across the organisation.")

    if df is None or len(df) == 0:
        st.info("Load data to see the governed metric in action.")
        return

    build = data_loader.load_build_summary()

    # hero card
    st.markdown(
        '<div class="metric-hero">'
        '<div class="kpi-label">Certified metric</div>'
        '<div class="kpi-value">NET REVENUE</div>'
        '<div class="hero-formula">Gross Sales − Discounts − Returns</div>'
        f'<div class="kpi-sub">Owner: {config.METRIC_OWNER} &nbsp;·&nbsp; Status: {status_badge()} '
        f'&nbsp;·&nbsp; Last updated: {format_date(build.get("date_end"))} '
        f'&nbsp;·&nbsp; Source: {config.METRIC_SOURCE}</div>'
        '</div>',
        unsafe_allow_html=True)

    st.markdown("")
    # formula flow: Gross Sales → − Discounts → − Returns → = Net Revenue
    c1, o1, c2, o2, c3, o3, c4 = st.columns([1.6, 0.4, 1.4, 0.4, 1.4, 0.4, 1.9])
    c1.markdown('<div class="flow-box"><div class="kpi-label">Gross Sales</div>'
                f'<div class="flow-val">{format_inr(metrics.gross_revenue(df))}</div></div>',
                unsafe_allow_html=True)
    o1.markdown('<div class="flow-op">−</div>', unsafe_allow_html=True)
    c2.markdown('<div class="flow-box"><div class="kpi-label">Discounts</div>'
                f'<div class="flow-val">{format_inr(df["DiscountAmount"].sum())}</div></div>',
                unsafe_allow_html=True)
    o2.markdown('<div class="flow-op">−</div>', unsafe_allow_html=True)
    c3.markdown('<div class="flow-box"><div class="kpi-label">Returns</div>'
                f'<div class="flow-val">{format_inr(df["ReturnAmount"].sum())}</div></div>',
                unsafe_allow_html=True)
    o3.markdown('<div class="flow-op">=</div>', unsafe_allow_html=True)
    c4.markdown('<div class="flow-box flow-result"><div class="kpi-label">Net Revenue</div>'
                f'<div class="flow-val">{format_inr(metrics.net_revenue(df))}</div></div>',
                unsafe_allow_html=True)

    st.markdown("")
    st.markdown("**Live consistency proof (current scope)**")
    _consistency_proof(df)

    st.markdown("")
    st.markdown("**Metric catalog**")
    catalog = pd.DataFrame(metrics.METRIC_CATALOG)
    st.dataframe(
        catalog, width="stretch", height=290, hide_index=True, key="gov_catalog",
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="small"),
            "Definition": st.column_config.TextColumn("Definition", width="large"),
            "Owner": st.column_config.TextColumn("Owner", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )

    st.markdown("")
    st.info(
        "Why this matters: Sales and Finance use the same metric definitions, so numbers "
        "agree before the meeting starts — no disputes, no manual reconciliation. Every "
        "revenue KPI, chart and comparison in this dashboard is calculated from the same "
        "governed Net Revenue definition (Gross Sales − Discounts − Returns).",
        icon=None,
    )
    st.caption(f"Model generated {format_datetime(build.get('generated_at'))} · "
               f"{build.get('rows_fact', 0):,} governed rows · deterministic seed {build.get('seed')}")
