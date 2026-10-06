"""Overview page — executive dashboard with KPIs, trends, targets and insights."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, config, forecast, insights, metrics
from src.formatting import delta_text, format_inr, format_int, format_pct
from src.ui import empty_state, insight_item, kpi_card, kpi_row, page_header, target_row

GRAINS = ["Daily", "Weekly", "Monthly", "Quarterly"]


def _kpi_cards(df: pd.DataFrame, prev_df: pd.DataFrame | None) -> list[str]:
    k = metrics.kpi_summary(df)
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}

    trend = metrics.revenue_trend(df, "Monthly")
    spark = charts.sparkline_svg(trend["NetRevenue"].tail(12).tolist())

    delta_rev, cls_rev = delta_text(k["net_revenue"], p.get("net_revenue"))
    delta_ord, cls_ord = delta_text(k["orders"], p.get("orders"))
    delta_units, cls_units = delta_text(k["units_sold"], p.get("units_sold"))
    delta_profit, cls_profit = delta_text(k["profit"], p.get("profit"))
    delta_aov, cls_aov = delta_text(k["aov"], p.get("aov"))

    # growth KPI is itself a percentage change
    if p.get("net_revenue"):
        growth = (k["net_revenue"] - p["net_revenue"]) / p["net_revenue"] * 100
        growth_val, growth_cls = format_pct(growth), ("delta-up" if growth >= 0 else "delta-down")
        growth_sub = f"{format_inr(k['net_revenue'] - p['net_revenue'])} vs previous period"
    else:
        growth_val, growth_cls, growth_sub = "—", "delta-flat", "no previous period in scope"

    return [
        kpi_card("Net Revenue", format_inr(k["net_revenue"]), delta_rev, cls_rev, spark),
        kpi_card("Revenue Growth", growth_val, growth_cls, growth_cls, sub=growth_sub),
        kpi_card("Orders", format_int(k["orders"]), delta_ord, cls_ord),
        kpi_card("Units Sold", format_int(k["units_sold"]), delta_units, cls_units),
        kpi_card("Gross Profit", format_inr(k["profit"]), delta_profit, cls_profit,
                 sub=f"{format_pct(k['profit_margin'])} margin"),
        kpi_card("Average Order Value", format_inr(k["aov"]), delta_aov, cls_aov),
    ]


def _trend_section(df: pd.DataFrame, prev_df: pd.DataFrame | None) -> None:
    c1, c2 = st.columns([2, 3])
    with c1:
        grain = st.radio("Grain", GRAINS, horizontal=True, key="ov_grain")
    with c2:
        compare = st.toggle("Compare with previous period", value=True, key="ov_compare")

    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if compare and prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        compare_name="Previous period", y_title="Net Revenue (₹ Cr)", height=360)
    st.plotly_chart(fig, width="stretch", key="ov_trend")


def _forecast_section(df: pd.DataFrame) -> None:
    """Linear trend forecast of the governed monthly series + confidence band."""
    result = forecast.forecast_monthly(df)
    if result is None:
        return
    hist, fc = result
    st.markdown("")
    st.markdown("**Outlook — linear trend forecast (next 3 months)**")
    fig = charts.forecast_chart(hist, fc, height=300)
    st.plotly_chart(fig, width="stretch", key="ov_forecast")
    st.caption(f"Simple linear projection of the governed monthly series with a 95% band — "
               f"for illustration; production forecasting would use seasonal models. "
               f"Next month: {format_inr(fc['Forecast'].iloc[0])} "
               f"(range {format_inr(fc['Lo'].iloc[0])} – {format_inr(fc['Hi'].iloc[0])}).")


def _region_and_mix(df: pd.DataFrame) -> None:
    left, right = st.columns([3, 2])
    with left:
        by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
        fig = charts.column_chart(
            by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
            hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
            title="Revenue by Region (₹ Cr)", height=330)
        st.plotly_chart(fig, width="stretch", key="ov_region")
    with right:
        by_cat = metrics.aggregate_by(df, ["Category"]).sort_values("NetRevenue", ascending=False)
        fig = charts.donut_chart(by_cat, "Category", "NetRevenue",
                                 center_title="Net Revenue", center_value=format_inr(by_cat["NetRevenue"].sum()),
                                 height=330)
        st.plotly_chart(fig, width="stretch", key="ov_mix")


def _products_and_profitability(df: pd.DataFrame) -> None:
    left, right = st.columns([2, 3])
    with left:
        by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
        fig = charts.hbar_chart(
            by_prod, x="ProductName", y=[v / 1e7 for v in by_prod["NetRevenue"]],
            hover_texts=[f"{p} · {format_inr(v)}" for p, v in zip(by_prod["ProductName"], by_prod["NetRevenue"])],
            title="Top 10 Products by Net Revenue (₹ Cr)", height=400)
        st.plotly_chart(fig, width="stretch", key="ov_top_products")
    with right:
        by_prod = metrics.aggregate_by(df, ["ProductName"])
        fig = charts.scatter_quadrant(by_prod, "NetRevenue", "Margin", "ProductName",
                                      x_title="Net Revenue (₹ Cr)", y_title="Profit Margin (%)", height=400)
        st.plotly_chart(fig, width="stretch", key="ov_scatter")


def _targets(full_df: pd.DataFrame, role: str = "Executive") -> None:
    """Actual vs target for the latest complete month / quarter / trailing 12 months."""
    if full_df is None or len(full_df) == 0:
        return
    end = full_df["Date"].max()
    latest_month_period = end.to_period("M") - 1  # last COMPLETE month
    m = full_df[full_df["Date"].dt.to_period("M") == latest_month_period]
    latest_q_period = end.to_period("Q") - 1      # last COMPLETE quarter
    q = full_df[full_df["Date"].dt.to_period("Q") == latest_q_period]
    ttm = full_df[full_df["Date"] >= end - pd.Timedelta(days=365)]

    rows = [
        (f"Monthly target · {latest_month_period.strftime('%b %Y')}",
         metrics.net_revenue(m), config.MONTHLY_TARGET),
        (f"Quarterly target · Q{latest_q_period.quarter} {latest_q_period.year}",
         metrics.net_revenue(q), config.QUARTERLY_TARGET),
        ("Annual target · trailing 12 months",
         metrics.net_revenue(ttm), config.ANNUAL_TARGET),
    ]
    cols = st.columns(3)
    for col, (label, actual, target) in zip(cols, rows):
        pct = actual / target * 100 if target else 0
        col.markdown(target_row(label, pct, format_inr(actual), format_inr(target)),
                     unsafe_allow_html=True)
    # company targets vs regional actuals would mislead — clarify for restricted roles
    from src import rls as _rls
    if _rls.is_restricted(role):
        st.caption("Targets are company-wide; actuals reflect your role's region scope — "
                   "shown for context, not performance judgement.")


def render(ctx: dict) -> None:
    df, prev_df, full_df = ctx["df"], ctx["prev_df"], ctx["full_df"]
    page_header("Business Performance Overview",
                "A single trusted view of revenue, growth and commercial performance.")

    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    kpi_row(_kpi_cards(df, prev_df))
    st.markdown("")
    _trend_section(df, prev_df)
    _forecast_section(df)
    _region_and_mix(df)
    _products_and_profitability(df)

    st.markdown("")
    left, right = st.columns(2)
    with left:
        st.markdown("**Executive Insights**")
        for ins in insights.generate_insights(df)[:5]:
            insight_item(ins["level"], ins["title"], ins["text"])
    with right:
        st.markdown("**Attention Required**")
        alerts = insights.generate_alerts(df)
        if alerts:
            for a in alerts[:5]:
                insight_item(a["level"], a["title"], a["text"])
        else:
            insight_item("positive", "✓ No flags raised",
                         "No region declines, return spikes or margin warnings in the current scope.")

    st.markdown("")
    st.markdown("**Business Targets**")
    _targets(full_df, ctx["role"])
