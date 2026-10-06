"""Regions page — territory/region performance with drill-down."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, metrics
from src.formatting import delta_text, format_inr, format_int, format_pct
from src.ui import empty_state, kpi_card, kpi_row, page_header

METRIC_MAP = {
    "Net Revenue": "NetRevenue",
    "Profit": "Profit",
    "Orders": "Orders",
    "Units Sold": "Quantity",
}


def _ranked(df: pd.DataFrame, prev_df: pd.DataFrame | None) -> pd.DataFrame:
    col = METRIC_MAP[st.session_state.get("rg_metric", "Net Revenue")]
    by_region = metrics.aggregate_by(df, ["Region"])
    if prev_df is not None and len(prev_df) and col == "NetRevenue":
        prev = metrics.aggregate_by(prev_df, ["Region"])[["Region", "NetRevenue"]].rename(
            columns={"NetRevenue": "PrevNet"})
        by_region = by_region.merge(prev, on="Region", how="left")
    return by_region.sort_values(col, ascending=False)


def _overview(df: pd.DataFrame, prev_df: pd.DataFrame | None) -> None:
    c1, _ = st.columns([2, 3])
    with c1:
        st.selectbox("Rank by", list(METRIC_MAP), key="rg_metric")
    by_region = _ranked(df, prev_df)
    col = METRIC_MAP[st.session_state.get("rg_metric", "Net Revenue")]

    left, right = st.columns([3, 2])
    with left:
        is_money = col in ("NetRevenue", "Profit")
        ys = [v / 1e7 for v in by_region[col]] if is_money else by_region[col].tolist()
        hovers = ([format_inr(v) for v in by_region[col]] if is_money
                  else [format_int(v) for v in by_region[col]])
        labels = [f"{r} · {h}" for r, h in zip(by_region["Region"], hovers)]
        fig = charts.column_chart(by_region, x="Region", y=ys, hover_texts=labels,
                                  title=f"{st.session_state.get('rg_metric', 'Net Revenue')} by Region"
                                        + (" (₹ Cr)" if is_money else ""),
                                  height=340)
        st.plotly_chart(fig, width="stretch", key="rg_rank")
    with right:
        fig = charts.donut_chart(by_region, "Region", "NetRevenue",
                                 center_title="Net Revenue",
                                 center_value=format_inr(by_region["NetRevenue"].sum()), height=340)
        st.plotly_chart(fig, width="stretch", key="rg_mix")

    # growth by region (uses the governed previous-period window)
    if prev_df is not None and len(prev_df) and "PrevNet" in by_region.columns:
        st.markdown("")
        st.markdown("**Growth by region (vs previous period)**")
        g = by_region.copy()
        g["Growth"] = (g["NetRevenue"] - g["PrevNet"]) / g["PrevNet"] * 100
        g = g.dropna(subset=["Growth"]).sort_values("Growth", ascending=False)
        if len(g):
            fig = charts.column_chart(
                g, x="Region", y=g["Growth"].tolist(),
                hover_texts=[f"{r} · {v:+.1f}%" for r, v in zip(g["Region"], g["Growth"])],
                height=260)
            fig.add_hline(y=0, line=dict(color="#475569", width=1))
            st.plotly_chart(fig, width="stretch", key="rg_growth")
            best, worst = g.iloc[0], g.iloc[-1]
            st.caption(f"Leader: {best['Region']} ({best['Growth']:+.1f}%) · "
                       f"Laggard: {worst['Region']} ({worst['Growth']:+.1f}%)")

    st.markdown("")
    st.markdown("**Territory map**")
    by_terr_all = metrics.aggregate_by(df, ["Territory", "Region"])
    fig = charts.map_bubble_chart(by_terr_all, height=420)
    st.plotly_chart(fig, width="stretch", key="rg_map")
    st.caption("Bubble size = Net Revenue, colour = region. Built-in Plotly geo layers — "
               "no external map dependencies, matching the PS31 reliability guidance.")


def _detail(df: pd.DataFrame, prev_df: pd.DataFrame | None) -> None:
    st.markdown("")
    st.markdown("**Region detail**")
    regions = sorted(df["Region"].unique().tolist())
    default = st.session_state.get("rg_selected", regions[0])
    region = st.selectbox("Select region", regions,
                          index=regions.index(default) if default in regions else 0, key="rg_selector")
    st.session_state["rg_selected"] = region
    rd = df[df["Region"] == region]
    if len(rd) == 0:
        empty_state("No data for this region in the current scope", "Widen the filters.")
        return
    rp = prev_df[prev_df["Region"] == region] if prev_df is not None and len(prev_df) else None

    k = metrics.kpi_summary(rd)
    p = metrics.kpi_summary(rp) if rp is not None and len(rp) else {}
    d_rev, c_rev = delta_text(k["net_revenue"], p.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    kpi_row([
        kpi_card(f"{region} · Net Revenue", format_inr(k["net_revenue"]), d_rev, c_rev),
        kpi_card("Orders", format_int(k["orders"]), d_ord, c_ord),
        kpi_card("Profit", format_inr(k["profit"]), sub=f"{format_pct(k['profit_margin'])} margin"),
        kpi_card("Return Rate", format_pct(k["return_rate"])),
    ])

    # top territories in this region
    by_terr = metrics.aggregate_by(rd, ["Territory"]).sort_values("NetRevenue", ascending=False)
    total = k["net_revenue"] or 1
    by_terr["Share"] = by_terr["NetRevenue"] / total * 100
    left, right = st.columns([2, 3])
    with left:
        fig = charts.hbar_chart(
            by_terr, x="Territory", y=[v / 1e7 for v in by_terr["NetRevenue"]],
            hover_texts=[f"{t} · {format_inr(v)} ({s:.1f}%)"
                         for t, v, s in zip(by_terr["Territory"], by_terr["NetRevenue"], by_terr["Share"])],
            title="Top Territories (₹ Cr)", height=300)
        st.plotly_chart(fig, width="stretch", key="rg_terr")
        st.caption(f"Top territory: {by_terr.iloc[0]['Territory']} ({by_terr.iloc[0]['Share']:.1f}% of {region}) · "
                   f"Smallest: {by_terr.iloc[-1]['Territory']} ({by_terr.iloc[-1]['Share']:.1f}%)")
    with right:
        trend = metrics.revenue_trend(rd, "Monthly")
        fig = charts.revenue_area_chart(
            trend, x="Label", y=[v / 1e7 for v in trend["NetRevenue"]],
            hover_texts=[format_inr(v) for v in trend["NetRevenue"]],
            name=f"{region} Net Revenue", y_title="Net Revenue (₹ Cr)", height=300)
        st.plotly_chart(fig, width="stretch", key="rg_trend")


def render(ctx: dict) -> None:
    df, prev_df = ctx["df"], ctx["prev_df"]
    page_header("Regional Performance",
                "Territory-level analysis: revenue, growth, profit and contribution.")
    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return
    _overview(df, prev_df)
    _detail(df, prev_df)
