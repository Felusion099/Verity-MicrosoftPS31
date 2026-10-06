"""Customers page — segment behaviour and top customers."""

from __future__ import annotations

import streamlit as st

from src import charts, metrics
from src.formatting import format_inr, format_int, format_pct
from src.ui import empty_state, kpi_card, kpi_row, page_header


def render(ctx: dict) -> None:
    df = ctx["df"]
    page_header("Customer Analysis",
                "Customer segments, order behaviour and top accounts.")
    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    by_seg = metrics.aggregate_by(df, ["Segment"]).sort_values("NetRevenue", ascending=False)
    kpi_row([
        kpi_card("Customers in scope", format_int(int(df["CustomerID"].nunique()))),
        kpi_card("Segments", format_int(len(by_seg))),
        kpi_card("Avg Order Value", format_inr(metrics.aov(df))),
        kpi_card("Return Rate", format_pct(metrics.return_rate(df))),
    ])

    left, right = st.columns(2)
    with left:
        fig = charts.donut_chart(by_seg, "Segment", "NetRevenue",
                                 center_title="Net Revenue",
                                 center_value=format_inr(by_seg["NetRevenue"].sum()), height=320)
        st.plotly_chart(fig, width="stretch", key="cu_mix")
    with right:
        fig = charts.column_chart(
            by_seg, x="Segment", y=by_seg["Orders"].tolist(),
            hover_texts=[f"{s} · {format_int(o)} orders" for s, o in zip(by_seg["Segment"], by_seg["Orders"])],
            title="Orders by Segment", height=320)
        st.plotly_chart(fig, width="stretch", key="cu_orders")

    st.markdown("")
    st.markdown("**Segment economics**")
    seg_view = by_seg[["Segment", "NetRevenue", "Orders", "AOV", "Margin", "ReturnRate"]].copy()
    st.dataframe(seg_view, width="stretch", height=200, hide_index=True, key="cu_seg",
                 column_config={
                     "Segment": st.column_config.TextColumn("Segment", width="small"),
                     "NetRevenue": st.column_config.NumberColumn("Net Revenue", format="₹,.0f"),
                     "Orders": st.column_config.NumberColumn("Orders", format=",d"),
                     "AOV": st.column_config.NumberColumn("Avg Order Value", format="₹,.0f"),
                     "Margin": st.column_config.NumberColumn("Margin %", format="%.1f"),
                     "ReturnRate": st.column_config.NumberColumn("Return %", format="%.1f"),
                 })

    st.markdown("")
    st.markdown("**Top 15 customers by Net Revenue**")
    top = metrics.aggregate_by(df, ["CustomerID", "CustomerName", "Segment"]) \
        .sort_values("NetRevenue", ascending=False).head(15)
    st.dataframe(
        top[["CustomerID", "CustomerName", "Segment", "Orders", "NetRevenue", "AOV"]],
        width="stretch", height=380, hide_index=True, key="cu_top",
        column_config={
            "CustomerID": st.column_config.TextColumn("Customer ID", width="small"),
            "CustomerName": st.column_config.TextColumn("Customer", width="medium"),
            "Segment": st.column_config.TextColumn("Segment", width="small"),
            "Orders": st.column_config.NumberColumn("Orders", format=",d"),
            "NetRevenue": st.column_config.NumberColumn("Net Revenue", format="₹,.0f"),
            "AOV": st.column_config.NumberColumn("Avg Order Value", format="₹,.0f"),
        },
    )
