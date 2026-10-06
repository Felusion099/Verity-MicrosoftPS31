"""Revenue page — governed revenue analysis with drill-down and transactions."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, metrics
from src.formatting import delta_text, format_inr, format_int, format_pct
from src.ui import empty_state, kpi_card, kpi_row, page_header

TRANS_COLS = ["OrderID", "Date", "Region", "Territory", "ProductName",
              "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue", "Profit"]


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


def _what_if(df: pd.DataFrame) -> None:
    """What-if discount simulator — recomputed from the governed formula, honestly."""
    st.markdown("")
    st.markdown("**What-if: discount simulator**")
    pct = st.slider("Additional discount on all transactions (%)",
                    min_value=0.0, max_value=15.0, value=0.0, step=0.5, key="rv_whatif")
    gross = metrics.gross_revenue(df)
    disc = float(df["DiscountAmount"].sum())
    rets = float(df["ReturnAmount"].sum())
    cost = metrics.total_cost(df)
    cur_net = gross - disc - rets
    new_net = max(0.0, gross - disc * (1 + pct / 100.0) - rets)
    cur_profit, new_profit = cur_net - cost, new_net - cost
    cur_margin = cur_profit / cur_net * 100 if cur_net > 0 else 0.0
    new_margin = new_profit / new_net * 100 if new_net > 0 else 0.0
    d_net, c_net = delta_text(new_net, cur_net) if pct else ("—", "delta-flat")
    d_m, c_m = delta_text(new_margin, cur_margin) if pct else ("—", "delta-flat")
    kpi_row([
        kpi_card("Current Net Revenue", format_inr(cur_net),
                 sub=f"{format_pct(cur_margin)} margin"),
        kpi_card(f"Simulated (+{pct:.1f}% discount)", format_inr(new_net), d_net, c_net,
                 sub=f"{format_pct(new_margin)} margin ({d_m})"),
        kpi_card("Revenue at risk", format_inr(max(0.0, cur_net - new_net)),
                 sub=f"{format_pct(cur_margin - new_margin)} margin lost" if pct else "no simulation applied"),
    ])
    st.caption("Simulated on the current filtered scope using the governed formula "
               "(Gross − Discounts − Returns) — honest illustration, not a prediction.")


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
        width="stretch", height=400, hide_index=True,
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
    df, prev_df = ctx["df"], ctx["prev_df"]
    page_header("Revenue Analysis",
                "One governed Net Revenue definition — drill from company to transaction.")

    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    # headline KPIs for the current scope
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
    # trend for the current scope (global filters only)
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
    st.plotly_chart(fig, width="stretch", key="rv_trend")

    st.markdown("")
    st.markdown("**Drill-down**")
    pool = _breadcrumb(df)

    # detail KPIs for the drilled scope
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
            st.plotly_chart(fig, width="stretch", key="rv_terr")
        with right:
            by_chan = metrics.aggregate_by(pool, ["SalesChannel"]).sort_values("NetRevenue", ascending=False)
            fig = charts.column_chart(
                by_chan, x="SalesChannel", y=[v / 1e7 for v in by_chan["NetRevenue"]],
                hover_texts=[f"{c} · {format_inr(v)}" for c, v in zip(by_chan["SalesChannel"], by_chan["NetRevenue"])],
                title="Revenue by Channel (₹ Cr)", height=300)
            st.plotly_chart(fig, width="stretch", key="rv_chan")

    _what_if(df)
    _transaction_table(pool)
