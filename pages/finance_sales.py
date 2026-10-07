"""Finance ↔ Sales Reconciliation page — the core PS31 page showing
Finance expectations vs Sales actuals with variance analysis."""

from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from src import metrics
from src.formatting import delta_text, format_inr, format_int, format_pct
from src.ui import empty_state, kpi_card, kpi_row, page_header
from src.data_loader import load_finance_plan


def render(ctx: dict) -> None:
    from src import metrics
    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row, page_header, empty_state
    import plotly.graph_objects as go
    import plotly.express as px

    page_header("Finance ↔ Sales Reconciliation",
                "Finance expected X. Sales delivered Y. Variance = Z. One governed definition.")

    df = ctx["df"]
    prev_df = ctx["prev_df"]

    if df is None or len(df) == 0:
        from src.ui import empty_state
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    # Headline KPIs for the current scope
    k = metrics.kpi_summary(df)
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}

    d_rev, c_rev = delta_text(k["net_revenue"], p.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))

    kpi_row([
        kpi_card("Net Revenue", format_inr(k["net_revenue"]), d_rev, c_rev,
                 sub=f"{format_int(k['orders'])} orders · {format_int(k['units_sold'])} units"),
        kpi_card("Orders", format_int(k["orders"]), d_ord, c_ord),
        kpi_card("Average Order Value", format_inr(k["aov"]), d_ach, c_ach),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, use_container_width=True, key="rv_trend")

    st.markdown("")
    st.markdown("**Drill-down**")
    pool = _breadcrumb(df)

    # Detail KPIs for the drilled scope
    pk = metrics.kpi_summary(pool)
    kpi_row([
        kpi_card("Drill-down Net Revenue", format_inr(pk["net_revenue"])),
        kpi_card("Drill-down Orders", format_int(pk["orders"])),
        kpi_card("Drill-down Margin", format_pct(pk["profit_margin"])),
        kpi_card("Drill-down Return Rate", format_pct(pk["return_rate"])),
    ])

    if len(pool):
        left, right = st.columns([3, 2])
        with left:
            by_terr = metrics.aggregate_by(pool, ["Territory"]).sort_values("NetRevenue", ascending=False).head(8)
            fig = charts.hbar_chart(
                by_terr, x="Territory", y=[v / 1e7 for v in by_terr["NetRevenue"]],
                hover_texts=[f"{t} · {format_inr(v)}" for t, v in zip(by_terr["Territory"], by_terr["NetRevenue"])],
                title="Net Revenue by Territory (₹ Cr)", height=300)
            st.plotly_chart(fig, use_container_width=True, key="rv_terr")
        with right:
            by_chan = metrics.aggregate_by(pool, ["SalesChannel"]).sort_values("NetRevenue", ascending=False)
            fig = charts.column_chart(
                by_chan, x="SalesChannel", y=[v / 1e7 for v in by_chan["NetRevenue"]],
                hover_texts=[f"{c} · {format_inr(v)}" for c, v in zip(by_chan["SalesChannel"], by_chan["NetRevenue"])],
                title="Revenue by Channel (₹ Cr)", height=300)
            st.plotly_chart(fig, use_container_width=True, key="rv_chan")

    _transaction_table(pool)


def _breadcrumb(df: pd.DataFrame) -> pd.DataFrame:
    """Company → Region → Territory → Category → Product → Transaction."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        region = st.selectbox("Region", ["All Regions"] + sorted(df["Region"].unique().tolist()),
                              key="rv_region")
    pool = df[df["Region"] == region] if region != "All Regions" else df
    with c2:
        territory = st.selectbox("Territory", ["All Territories"] + sorted(pool["Territory"].unique().tolist()),
                                 key="rv_territory")
    pool = pool[pool["Territory"] == territory] if territory != "All Territories" else pool
    with c3:
        category = st.selectbox("Category", ["All Categories"] + sorted(pool["Category"].unique().tolist()),
                                key="rv_category")
    pool = pool[pool["Category"] == category] if category != "All Categories" else pool
    with c4:
        product = st.selectbox("Product", ["All Products"] + sorted(pool["ProductName"].unique().tolist()),
                               key="rv_product")
    return pool[pool["ProductName"] == product] if product != "All Products" else pool


def _transaction_table(pool: pd.DataFrame) -> None:
    st.markdown("")
    st.markdown("**Transactions**")
    search = st.text_input("Search transactions (order ID, product, territory, customer)",
                           placeholder="e.g. ORD-2026-00123 or Laptops", key="rv_search")
    view = pool[TRANS_COLS].copy()
    if search.strip():
        q = search.strip().lower()
        view = view[view.apply(lambda r: q in str(r["OrderID"]).lower()
                               or q in str(r["ProductName"]).lower()
                               or q in str(r["Territory"]).lower()
                               or q in str(r["Region"]).lower(), axis=1)]
    view["Date"] = pd.to_datetime(view["Date"]).dt.date
    st.dataframe(
        view,
        use_container_width=True, height=400, hide_index=True,
        column_config={
            "OrderID": st.column_config.TextColumn("Order ID", width="medium"),
            "Date": st.column_config.DateColumn("Date", width="small"),
            "Region": st.column_config.TextColumn("Region", width="small"),
            "Territory": st.column_config.TextColumn("Territory", width="small"),
            "ProductName": st.column_config.TextColumn("Product", width="large"),
            "Quantity": st.column_config.NumberColumn("Qty", width="small"),
            "GrossSales": st.column_config.NumberColumn("Gross Sales", format="₹,.0f"),
            "DiscountAmount": st.column_config.NumberColumn("Discount", format="₹,.0f"),
            "ReturnAmount": st.column_config.NumberColumn("Returns", format="₹,.0f"),
            "NetRevenue": st.column_config.NumberColumn("Net Revenue", format="₹,.0f"),
            "Profit": st.column_config.NumberColumn("Profit", format="₹,.0f"),
        },
    )
    st.caption(f"{len(view):,} transaction line items shown (governed Net Revenue per row).")


def render(ctx: dict) -> None:
    from src import metrics, charts
    from src.formatting import delta_text, format_inr, format_int, format_pct
    from src.ui import empty_state, kpi_card, kpi_row, page_header

    page_header("Revenue Analysis",
                "One governed Net Revenue definition — drill from company to transaction.")

    df = ctx["df"]
    prev_df = ctx["prev_df"]

    if df is None or len(df) == 0:
        from src.ui import empty_state
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    # Headline KPIs for the current scope
    k = metrics.kpi_summary(df)
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}
    d_rev, c_rev = delta_text(k["net_revenue"], p.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))
    kpi_row([
        kpi_card("Net Revenue", format_inr(k["net_revenue"]), d_rev, c_rev,
                 sub=f"{format_int(k['orders'])} orders · {format_int(k['units_sold'])} units"),
        kpi_card("Orders", format_int(k["orders"]), d_ord, c_ord),
        kpi_card("Average Order Value", format_inr(k["aov"]), d_aov, c_aov),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, use_container_width=True, key="rv_trend")

    st.markdown("")
    _region_and_mix(df)
    _products_and_profitability(df)

    st.markdown("")
    _what_if(df)


def _region_and_mix(df: pd.DataFrame) -> None:
    left, right = st.columns([3, 2])
    with left:
        by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
        fig = charts.column_chart(
            by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
            hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
            title="Revenue by Region (₹ Cr)", height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_region")
    with right:
        by_cat = metrics.aggregate_by(df, ["Category"]).sort_values("NetRevenue", ascending=False)
        fig = charts.donut_chart(by_cat, "Category", "NetRevenue",
                                 center_title="Net Revenue", center_value=format_inr(by_cat["NetRevenue"].sum()),
                                 height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_mix")


def _products_and_profitability(df: pd.DataFrame) -> None:
    left, right = st.columns([2, 3])
    with left:
        by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
        fig = charts.hbar_chart(
            by_prod, x="ProductName", y=[v / 1e7 for v in by_prod["NetRevenue"]],
            hover_texts=[f"{p} · {format_inr(v)}" for p, v in zip(by_prod["ProductName"], by_prod["NetRevenue"])],
            title="Top 10 Products by Net Revenue (₹ Cr)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_top_products")
    with right:
        by_prod = metrics.aggregate_by(df, ["ProductName"])
        fig = charts.scatter_quadrant(by_prod, "NetRevenue", "Margin", "ProductName",
                                      x_title="Net Revenue (₹ Cr)", y_title="Profit Margin (%)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_scatter")


def _what_if(df: pd.DataFrame) -> None:
    """What-if discount simulator."""
    st.markdown("")
    st.markdown("**What-if: Discount Simulator**")
    pct = st.slider("Additional discount on all transactions (%)",
                    min_value=0.0, max_value=15.0, value=0.0, step=0.5, key="rv_whatif")
    gross = metrics.gross_revenue(df)
    disc = float(df["DiscountAmount"].sum())
    ret = float(df["ReturnAmount"].sum())
    cost = float(df["Cost"].sum())
    cur_net = gross - disc - rets
    new_net = max(0.0, gross - disc * (1 + pct / 100.0) - rets)
    cur_profit, new_profit = cur_net - cost, new_net - cost
    d_rev, c_rev = delta_text(cur_net, prev.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))
    kpi_row([
        kpi_card("Current Net Revenue", format_inr(cur_net), delta_text(cur_net, prev.get("net_revenue")), "delta-flat",
                 sub=f"{format_int(k['orders'])} orders · {format_int(k['units_sold'])} units"),
        kpi_card("Orders", format_int(k["orders"]), d_ord, c_ord),
        kpi_card("Average Order Value", format_inr(k["aov"]), d_aov, c_aov),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, use_container_width=True, key="rv_trend")

    st.markdown("")
    _region_and_mix(df)
    _products_and_profitability(df)
    _what_if(df)


def _region_and_mix(df: pd.DataFrame) -> None:
    left, right = st.columns([3, 2])
    with left:
        by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
        fig = charts.column_chart(
            by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
            hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
            title="Revenue by Region (₹ Cr)", height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_region")
    with right:
        by_cat = metrics.aggregate_by(df, ["Category"]).sort_values("NetRevenue", ascending=False)
        fig = charts.donut_chart(by_cat, "Category", "NetRevenue",
                                 center_title="Net Revenue", center_value=format_inr(by_cat["NetRevenue"].sum()), height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_mix")


def _products_and_profitability(df: pd.DataFrame) -> None:
    left, right = st.columns([2, 3])
    with left:
        by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
        fig = charts.hbar_chart(
            by_prod, x="ProductName", y=[v / 1e7 for v in by_prod["NetRevenue"]],
            hover_texts=[f"{p} · {format_inr(v)}" for p, v in zip(by_prod["ProductName"], by_prod["NetRevenue"])],
            title="Top 10 Products by Net Revenue (₹ Cr)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_top_products")
    with right:
        by_prod = metrics.aggregate_by(df, ["ProductName"])
        fig = charts.scatter_quadrant(by_prod, "NetRevenue", "Margin", "ProductName",
                                      x_title="Net Revenue (₹ Cr)", y_title="Profit Margin (%)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_scatter")


def _what_if(df: pd.DataFrame) -> None:
    """What-if discount simulator."""
    st.markdown("")
    st.markdown("**What-if: Discount Simulator**")
    pct = st.slider("Additional discount on all transactions (%)",
                    min_value=0.0, max_value=15.0, value=0.0, step=0.5, key="rv_whatif")
    gross = metrics.gross_revenue(df)
    disc = float(df["DiscountAmount"].sum())
    rets = float(df["ReturnAmount"].sum())
    cost = metrics.total_cost(df)
    cur_net = gross - disc - rets
    new_net = max(0.0, gross - disc * (1 + pct / 100.0) - rets)
    cur_profit, new_profit = cur_net - cost, new_net - cost
    d_rev, c_rev = delta_text(cur_net, prev.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))
    kpi_row([
        kpi_card("Net Revenue", format_inr(cur_net), delta_text(cur_net, prev.get("net_revenue")), "delta-flat",
                 sub=f"{format_int(k['orders'])} orders · {format_int(k['units_sold'])} units"),
        kpi_card("Orders", format_int(k["orders"]), d_ord, c_ord),
        kpi_card("Average Order Value", format_inr(k["aov"]), d_aov, c_aov),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, use_container_width=True, key="rv_trend")

    st.markdown("")
    _region_and_mix(df)
    _products_and_profitability(df)
    _what_if(df)


def _region_and_mix(df: pd.DataFrame) -> None:
    left, right = st.columns([3, 2])
    with left:
        by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
        fig = charts.column_chart(by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
                                  hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
                                  title="Revenue by Region (₹ Cr)", height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_region")
    with right:
        by_cat = metrics.aggregate_by(df, ["Category"]).sort_values("NetRevenue", ascending=False)
        fig = charts.donut_chart(by_cat, "Category", "NetRevenue",
                                 center_title="Net Revenue", center_value=format_inr(by_cat["NetRevenue"].sum()), height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_mix")


def _products_and_profitability(df: pd.DataFrame) -> None:
    left, right = st.columns([2, 3])
    with left:
        by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
        fig = charts.hbar_chart(
            by_prod, x="ProductName", y=[v / 1e7 for v in by_prod["NetRevenue"]],
            hover_texts=[f"{p} · {format_inr(v)}" for p, v in zip(by_prod["ProductName"], by_prod["NetRevenue"])],
            title="Top 10 Products by Net Revenue (₹ Cr)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_top_products")
    with right:
        by_prod = metrics.aggregate_by(df, ["ProductName"])
        fig = charts.scatter_quadrant(by_prod, "NetRevenue", "Margin", "ProductName",
                                      x_title="Net Revenue (₹ Cr)", y_title="Profit Margin (%)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_scatter")


def _what_if(df: pd.DataFrame) -> None:
    """What-if discount simulator."""
    st.markdown("")
    st.markdown("**What-if: Discount Simulator**")
    pct = st.slider("Additional discount on all transactions (%)",
                    min_value=0.0, max_value=15.0, value=0.0, step=0.5, key="rv_whatif")
    gross = metrics.gross_revenue(df)
    disc = float(df["DiscountAmount"].sum())
    rets = float(df["ReturnAmount"].sum())
    cost = metrics.total_cost(df)
    cur_net = gross - disc - rets
    new_net = max(0.0, gross - disc * (1 + pct / 100.0) - rets)
    cur_profit, new_profit = cur_net - cost, new_net - cost
    d_rev, c_rev = delta_text(cur_net, prev.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))
    kpi_row([
        kpi_card("Net Revenue", format_inr(cur_net), d_rev, c_rev,
                 sub=f"{format_int(k['orders'])} orders"),
        kpi_card("Orders", format_int(k["orders"]), d_ord, c_ord),
        kpi_card("Average Order Value", format_inr(k["aov"]), d_aov, c_aov),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, use_container_width=True, key="rv_trend")

    st.markdown("")
    _region_and_mix(df)
    _products_and_profitability(df)
    _what_if(df)


def _region_and_mix(df: pd.DataFrame) -> None:
    left, right = st.columns([3, 2])
    with left:
        by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
        fig = charts.column_chart(by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
                                  hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
                                  title="Revenue by Region (₹ Cr)", height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_region")
    with right:
        by_cat = metrics.aggregate_by(df, ["Category"]).sort_values("NetRevenue", ascending=False)
        fig = charts.donut_chart(by_cat, "Category", "NetRevenue",
                                 center_title="Net Revenue", center_value=format_inr(by_cat["NetRevenue"].sum()), height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_mix")


def _products_and_profitability(df: pd.DataFrame) -> None:
    left, right = st.columns([2, 3])
    with left:
        by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
        fig = charts.hbar_chart(
            by_prod, x="ProductName", y=[v / 1e7 for v in by_prod["NetRevenue"]],
            hover_texts=[f"{p} · {format_inr(v)}" for p, v in zip(by_prod["ProductName"], by_prod["NetRevenue"])],
            title="Top 10 Products by Net Revenue (₹ Cr)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_top_products")
    with right:
        by_prod = metrics.aggregate_by(df, ["ProductName"])
        fig = charts.scatter_quadrant(by_prod, "NetRevenue", "Margin", "ProductName",
                                      x_title="Net Revenue (₹ Cr)", y_title="Profit Margin (%)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_scatter")


def _what_if(df: pd.DataFrame) -> None:
    """What-if discount simulator."""
    st.markdown("")
    st.markdown("**What-if: Discount Simulator**")
    pct = st.slider("Additional discount on all transactions (%)",
                    min_value=0.0, max_value=15.0, value=0.0, step=0.5, key="rv_whatif")
    gross = metrics.gross_revenue(df)
    disc = float(df["DiscountAmount"].sum())
    rets = float(df["ReturnAmount"].sum())
    cost = metrics.total_cost(df)
    cur_net = gross - disc - rets
    new_net = max(0.0, gross - disc * (1 + pct / 100.0) - rets)
    cur_profit, new_profit = cur_net - cost, new_net - cost
    d_rev, c_rev = delta_text(cur_net, prev.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))
    kpi_row([
        kpi_card("Net Revenue", format_inr(cur_net), d_rev, c_rev,
                 sub=f"{format_int(k['orders'])} orders"),
        kpi_card("Units Sold", format_int(k["quantity"])),
        kpi_card("Average Selling Price", format_inr(pd_rows["UnitPrice"].mean())),
        kpi_card("Discount Rate", format_pct(g["DiscountAmount"] / g["GrossSales"] * 100 if g["GrossSales"] else 0)),
        kpi_card("Profit", format_inr(cur_profit), d_pro, c_pro, sub=f"{format_pct(new_profit / cur_net * 100) if cur_net else 0} margin"),
        kpi_card("Return Rate", format_pct(g["ReturnRate"])),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, use_container_width=True, key="rv_trend")

    st.markdown("")
    _region_and_mix(df)
    _products_and_profitability(df)
    _what_if(df)


def _region_and_mix(df: pd.DataFrame) -> None:
    left, right = st.columns([3, 2])
    with left:
        by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
        fig = charts.column_chart(by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
                                  hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
                                  title="Revenue by Region (₹ Cr)", height=340)
        st.plotly_chart(fig, use_container_width=True, key="ov_region")
    with right:
        by_cat = metrics.aggregate_by(df, ["Category"]).sort_values("NetRevenue", ascending=False)
        fig = charts.donut_chart(by_cat, "Category", "NetRevenue",
                                 center_title="Net Revenue",
                                 center_value=format_inr(by_cat["NetRevenue"].sum()), height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_mix")


def _products_and_profitability(df: pd.DataFrame) -> None:
    left, right = st.columns([2, 3])
    with left:
        by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
        fig = charts.hbar_chart(
            by_prod, x="ProductName", y=[v / 1e7 for v in by_prod["NetRevenue"]],
            hover_texts=[f"{p} · {format_inr(v)}" for p, v in zip(by_prod["ProductName"], by_prod["NetRevenue"])],
            title="Top 10 Products by Net Revenue (₹ Cr)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_top_products")
    with right:
        by_prod = metrics.aggregate_by(df, ["ProductName"])
        fig = charts.scatter_quadrant(by_prod, "NetRevenue", "Margin", "ProductName",
                                      x_title="Net Revenue (₹ Cr)", y_title="Profit Margin (%)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_scatter")


def _what_if(df: pd.DataFrame) -> None:
    """What-if discount simulator."""
    st.markdown("")
    st.markdown("**What-if: Discount Simulator**")
    pct = st.slider("Additional discount on all transactions (%)",
                    min_value=0.0, max_value=15.0, value=0.0, step=0.5, key="rv_whatif")
    gross = metrics.gross_revenue(df)
    disc = float(df["DiscountAmount"].sum())
    rets = float(df["ReturnAmount"].sum())
    cost = metrics.total_cost(df)
    cur_net = gross - disc - rets
    new_net = max(0.0, gross - disc * (1 + pct / 100.0) - rets)
    cur_profit, new_profit = cur_net - cost, new_net - cost
    d_rev, c_rev = delta_text(cur_net, prev.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))
    kpi_row([
        kpi_card("Net Revenue", format_inr(cur_net), d_rev, c_rev,
                 sub=f"{format_int(k['orders'])} orders"),
        kpi_card("Units Sold", format_int(k["quantity"])),
        kpi_card("Average Selling Price", format_inr(pd_rows["UnitPrice"].mean())),
        kpi_card("Discount Rate", format_pct(g["DiscountAmount"] / g["GrossSales"] * 100 if g["GrossSales"] else 0)),
        kpi_card("Profit", format_inr(cur_profit), sub=f"{format_pct(new_profit / cur_net * 100) if cur_net else 0} margin"),
        kpi_card("Return Rate", format_pct(g["ReturnRate"])),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, use_container_width=True, key="rv_trend")

    st.markdown("")
    _region_and_mix(df)
    _products_and_profitability(df)
    _what_if(df)


def _region_and_mix(df: pd.DataFrame) -> None:
    left, right = st.columns([3, 2])
    with left:
        by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
        fig = charts.column_chart(by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
                                  hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
                                  title="Revenue by Region (₹ Cr)", height=340)
        st.plotly_chart(fig, use_container_width=True, key="ov_region")
    with right:
        by_cat = metrics.aggregate_by(df, ["Category"]).sort_values("NetRevenue", ascending=False)
        fig = charts.donut_chart(by_cat, "Category", "NetRevenue",
                                 center_title="Net Revenue",
                                 center_value=format_inr(by_cat["NetRevenue"].sum()), height=330)
        st.plotly_chart(fig, use_container_width=True, key="ov_mix")


def _products_and_profitability(df: pd.DataFrame) -> None:
    left, right = st.columns([2, 3])
    with left:
        by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
        fig = charts.hbar_chart(
            by_prod, x="ProductName", y=[v / 1e7 for v in by_prod["NetRevenue"]],
            hover_texts=[f"{p} · {format_inr(v)}" for p, v in zip(by_prod["ProductName"], by_prod["NetRevenue"])],
            title="Top 10 Products by Net Revenue (₹ Cr)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_top_products")
    with right:
        by_prod = metrics.aggregate_by(df, ["ProductName"])
        fig = charts.scatter_quadrant(by_prod, "NetRevenue", "Margin", "ProductName",
                                      x_title="Net Revenue (₹ Cr)", y_title="Profit Margin (%)", height=400)
        st.plotly_chart(fig, use_container_width=True, key="ov_scatter")


def _what_if(df: pd.DataFrame) -> None:
    """What-if discount simulator."""
    st.markdown("")
    st.markdown("**What-if: Discount Simulator**")
    pct = st.slider("Additional discount on all transactions (%)",
                    min_value=0.0, max_value=15.0, value=0.0, step=0.5, key="rv_whatif")
    gross = metrics.gross_revenue(df)
    disc = float(df["DiscountAmount"].sum())
    rets = float(df["ReturnAmount"].sum())
    cost = metrics.total_cost(df)
    cur_net = gross - disc - rets
    new_net = max(0.0, gross - disc * (1 + pct / 100.0) - rets)
    cur_profit, new_profit = cur_net - cost, new_net - cost
    d_rev, c_rev = delta_text(cur_net, prev.get("net_revenue"))
    d_ord, c_ord = delta_text(k["orders"], p.get("orders"))
    d_aov, c_aov = delta_text(k["aov"], p.get("aov"))
    kpi_row([
        kpi_card("Net Revenue", format_inr(cur_net), d_rev, c_rev,
                 sub=f"{format_int(k['orders'])} orders"),
        kpi_card("Units Sold", format_int(k["quantity"])),
        kpi_card("Average Selling Price", format_inr(pd_rows["UnitPrice"].mean())),
        kpi_card("Discount Rate", format_pct(g["DiscountAmount"] / g["GrossSales"] * 100 if g["GrossSales"] else 0)),
        kpi_card("Profit", format_inr(cur_profit), d_pro, c_pro, sub=f"{format_pct(new_profit / cur_net * 100) if cur_net else 0} margin"),
        kpi_card("Return Rate", format_pct(g["ReturnRate"])),
    ])

    st.markdown("")
    # Trend for the current scope (global filters only)
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="rv_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name=product, y_title="Net Revenue (₹ Cr)", height=300)
    st.plotly_chart(fig, use_container_width=True, key="pr_trend")