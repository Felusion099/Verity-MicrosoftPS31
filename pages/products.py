"""Products page — product rankings plus a full product detail view."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, metrics
from src.formatting import format_inr, format_int, format_pct
from src.ui import empty_state, kpi_card, kpi_row, page_header


def _rank_table(title: str, d: pd.DataFrame, cols: list[str], key: str) -> None:
    st.markdown(f"**{title}**")
    st.dataframe(d[cols], width="stretch", height=230, hide_index=True, key=key)


def _rankings(df: pd.DataFrame) -> None:
    by_prod = metrics.aggregate_by(df, ["ProductName"])
    base_cols = ["ProductName", "NetRevenue", "Orders", "Quantity", "Margin", "AOV"]
    top = by_prod.sort_values("NetRevenue", ascending=False).head(10)
    bottom = by_prod.sort_values("NetRevenue").head(10)
    fastest = metrics.window_growth_by(df, ["ProductName"], days=90, min_lines=10).head(10)
    margin = by_prod[by_prod["Lines"] >= 20].sort_values("Margin", ascending=False).head(10)
    # most discounted = highest average discount rate (line-level)
    avg_disc = df.groupby("ProductName").agg(
        DiscRate=("DiscountRate", "mean"),
        GrossSales=("GrossSales", "sum"),
        DiscountAmount=("DiscountAmount", "sum"),
        ReturnAmount=("ReturnAmount", "sum"),
    ).reset_index()
    avg_disc["NetRevenue"] = (avg_disc["GrossSales"] - avg_disc["DiscountAmount"]
                              - avg_disc["ReturnAmount"])  # governed formula
    avg_disc = avg_disc.sort_values("DiscRate", ascending=False).head(10)
    returns = by_prod[by_prod["Lines"] >= 20].sort_values("ReturnRate", ascending=False).head(10)

    c1, c2 = st.columns(2)
    with c1:
        _rank_table("Top 10 by Net Revenue", top, base_cols, "pr_top")
        _rank_table("Fastest growing (90d vs prior 90d)",
                    fastest[["ProductName", "Growth", "NetRevenue", "PrevNetRevenue", "Orders"]],
                    ["ProductName", "Growth", "NetRevenue", "PrevNetRevenue", "Orders"], "pr_fast")
        _rank_table("Most discounted (avg discount rate)",
                    avg_disc[["ProductName", "DiscRate", "NetRevenue"]],
                    ["ProductName", "DiscRate", "NetRevenue"], "pr_disc")
    with c2:
        _rank_table("Bottom 10 by Net Revenue", bottom, base_cols, "pr_bottom")
        _rank_table("Highest margin", margin[["ProductName", "Margin", "NetRevenue", "Profit"]],
                    ["ProductName", "Margin", "NetRevenue", "Profit"], "pr_margin")
        _rank_table("Highest return rate", returns[["ProductName", "ReturnRate", "Lines"]],
                    ["ProductName", "ReturnRate", "Lines"], "pr_returns")


def _detail(df: pd.DataFrame) -> None:
    st.markdown("")
    st.markdown("**Product detail**")
    products = sorted(df["ProductName"].unique().tolist())
    default = st.session_state.get("pr_selected", products[0])
    product = st.selectbox("Select product", products, index=products.index(default) if default in products else 0,
                           key="pr_selector")
    st.session_state["pr_selected"] = product
    pd_rows = df[df["ProductName"] == product]
    if len(pd_rows) == 0:
        empty_state("No transactions for this product in the current scope", "Widen the filters.")
        return

    g = metrics.aggregate_by(pd_rows, ["ProductName"]).iloc[0]
    kpi_row([
        kpi_card("Net Revenue", format_inr(g["NetRevenue"]),
                 sub=f"{format_int(g['Orders'])} orders"),
        kpi_card("Units Sold", format_int(g["Quantity"])),
        kpi_card("Average Selling Price", format_inr(pd_rows["UnitPrice"].mean())),
        kpi_card("Discount Rate", format_pct(g["DiscountAmount"] / g["GrossSales"] * 100 if g["GrossSales"] else 0)),
        kpi_card("Profit", format_inr(g["Profit"]), sub=f"{format_pct(g['Margin'])} margin"),
        kpi_card("Return Rate", format_pct(g["ReturnRate"])),
    ])

    trend = metrics.revenue_trend(pd_rows, "Monthly")
    fig = charts.revenue_area_chart(
        trend, x="Label", y=[v / 1e7 for v in trend["NetRevenue"]],
        hover_texts=[format_inr(v) for v in trend["NetRevenue"]],
        name=product, y_title="Net Revenue (₹ Cr)", height=300)
    st.plotly_chart(fig, width="stretch", key="pr_trend")


def render(ctx: dict) -> None:
    df = ctx["df"]
    page_header("Product Performance",
                "Ranked products, growth and margins — all from the governed model.")
    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return
    tab1, tab2 = st.tabs(["Rankings", "Product Detail"])
    with tab1:
        _rankings(df)
    with tab2:
        _detail(df)
