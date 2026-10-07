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


TRANS_COLS = ["OrderID", "Date", "Region", "Territory", "ProductName",
              "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue", "Profit"]


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

    finance_target = ctx.get("finance_target", 0)
    finance_forecast = ctx.get("finance_forecast", 0)
    expected_revenue = ctx.get("expected_revenue", 0)

    actual = k["net_revenue"]
    variance = actual - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - finance_forecast) / finance_forecast * 100) if finance_forecast else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row

    d_rev, c_rev = delta_text(k["net_revenue"], 0)
    d_var, c_var = delta_text(k["net_revenue"] - finance_target, 0)
    d_ach, c_ach = delta_text((k["net_revenue"] / finance_target * 100) if finance_target else 0, 0)

    kpi_row([
        kpi_card("Finance Target", format_inr(finance_target)),
        kpi_card("Finance Forecast", format_inr(finance_forecast)),
        kpi_card("Actual Net Revenue", format_inr(actual), d_rev, c_rev),
        kpi_card("Variance", format_inr(variance), d_var, c_var),
        kpi_card("Achievement %", format_pct(achievement), d_ach, c_ach),
        kpi_card("Forecast Accuracy", format_pct(forecast_accuracy)),
    ])

    st.markdown("")
    # Trend chart
    st.markdown("**Finance Target vs Actual Net Revenue Trend**")
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="fs_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, width="stretch", key="fs_trend")

    st.markdown("")
    st.markdown("**Variance by Region**")
    by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
    fp_region = fp.groupby("Region").agg({"FinanceTarget": "sum"}).reset_index()
    var_df = by_region.merge(fp_region, on="Region", how="left")
    var_df["Variance"] = var_df["NetRevenue"] - var_df["FinanceTarget"]
    var_df["VariancePct"] = (var_df["Variance"] / var_df["FinanceTarget"] * 100).where(var_df["FinanceTarget"] != 0, 0)

    fig = px.bar(var_df, x="Region", y="Variance", color="Variance",
                 color_continuous_scale=["#f87171", "#34d399"],
                 text=var_df["Variance"].apply(lambda x: format_inr(x)),
                 title="Variance vs Finance Target by Region (₹ Cr)")
    fig.update_layout(height=300)
    st.plotly_chart(fig, width="stretch", key="fs_var_region")

    st.markdown("")
    st.markdown("**Variance by Product Category**")
    by_cat = metrics.aggregate_by(df, ["Category"])
    fp_cat = fp.groupby("Category").agg({"FinanceTarget": "sum"}).reset_index()
    cat_var = by_cat.merge(fp_cat, on="Category", how="left")
    cat_var["Variance"] = cat_var["NetRevenue"] - cat_var["FinanceTarget"]
    cat_var["VariancePct"] = (cat_var["Variance"] / cat_var["FinanceTarget"] * 100).where(cat_var["FinanceTarget"] != 0, 0)

    fig = px.bar(cat_var.sort_values("Variance"), x="Category", y="Variance",
                 color="Variance", color_continuous_scale=["#f87171", "#34d399"],
                 text=cat_var["Variance"].apply(lambda x: f"₹{x/1e7:.1f}Cr"),
                 title="Variance by Category (₹ Cr)")
    fig.update_layout(height=350)
    st.plotly_chart(fig, width="stretch", key="fs_var_cat")

    st.markdown("")
    
    # Drill-down table
    st.markdown("**Transaction-Level Detail**")
    detail = df[["OrderID", "Date", "Region", "Territory", "ProductName",
                 "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue", "Profit"]].copy()
    detail["Date"] = pd.to_datetime(detail["Date"]).dt.date
    st.dataframe(
        detail.sort_values("NetRevenue", ascending=False),
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
        height=400, hide_index=True, key="fs_detail"
    )


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

    k = metrics.kpi_summary(df)
    prev_df = ctx["prev_df"]
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}

    from src.data_loader import load_finance_plan
    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(ctx["df"]["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = metrics.kpi_summary(df)["net_revenue"]
    variance = actual - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - fp["FinanceForecast"].sum()) / fp["FinanceForecast"].sum() * 100) if fp["FinanceForecast"].sum() else 0

    d_rev, c_rev = delta_text(k["net_revenue"], p.get("net_revenue"))
    d_var, c_var = delta_text(k["net_revenue"] - finance_target, 0)
    d_ach, c_ach = delta_text((k["net_revenue"] / finance_target * 100) if finance_target else 0, 0)

    kpi_row([
        kpi_card("Finance Target", format_inr(finance_target)),
        kpi_card("Finance Forecast", format_inr(finance_forecast)),
        kpi_card("Actual Net Revenue", format_inr(actual), d_rev, c_rev),
        kpi_card("Variance", format_inr(variance), d_var, c_var),
        kpi_card("Achievement %", format_pct(achievement), d_ach, c_ach),
        kpi_card("Forecast Accuracy", format_pct(forecast_accuracy)),
    ])

    st.markdown("")
    # Trend chart
    grain = st.radio("Grain", ["Daily", "Weekly", "Monthly", "Quarterly"],
                     horizontal=True, key="fs_grain")
    cur = metrics.revenue_trend(df, grain)
    prev = metrics.revenue_trend(prev_df, grain) if prev_df is not None and len(prev_df) else None
    fig = charts.revenue_area_chart(
        cur, x="Label", y=[v / 1e7 for v in cur["NetRevenue"]],
        hover_texts=[format_inr(v) for v in cur["NetRevenue"]],
        name="Net Revenue", compare_df=prev,
        compare_x="Label" if prev is not None else None,
        compare_y=[v / 1e7 for v in prev["NetRevenue"]] if prev is not None else None,
        y_title="Net Revenue (₹ Cr)", height=320)
    st.plotly_chart(fig, width="stretch", key="fs_trend")

    st.markdown("")
    st.markdown("**Variance by Region**")
    by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
    fig = charts.column_chart(
        by_region, x="Region", y=[v / 1e7 for v in by_region["NetRevenue"]],
        hover_texts=[f"{r} · {format_inr(v)}" for r, v in zip(by_region["Region"], by_region["NetRevenue"])],
        title="Revenue by Region (₹ Cr)", height=340)
    st.plotly_chart(fig, width="stretch", key="fs_region")

    st.markdown("")
    st.markdown("**Variance by Region**")
    by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
    fp_region = fp.groupby("Region").agg({"FinanceTarget": "sum"}).reset_index()
    var_df = by_region.merge(fp_region, on="Region", how="left")
    var_df["Variance"] = var_df["NetRevenue"] - var_df["FinanceTarget"]
    var_df["VariancePct"] = (var_df["Variance"] / var_df["FinanceTarget"] * 100).where(var_df["FinanceTarget"] != 0, 0)

    fig = charts.column_chart(
        var_df, x="Region", y=[v / 1e7 for v in var_df["Variance"]],
        hover_texts=[format_inr(v) for v in var_df["Variance"]],
        title="Variance vs Finance Target by Region (₹ Cr)", height=300)
    st.plotly_chart(fig, width="stretch", key="fs_var_region")

    st.markdown("")
    st.markdown("**Variance by Category**")
    by_cat = metrics.aggregate_by(df, ["Category"])
    fp_cat = fp.groupby("Category").agg({"FinanceTarget": "sum"}).reset_index()
    cat_var = by_cat.merge(fp_cat, on="Category", how="left")
    cat_var["Variance"] = cat_var["NetRevenue"] - cat_var["FinanceTarget"]
    cat_var["VariancePct"] = (cat_var["Variance"] / cat_var["FinanceTarget"] * 100).where(cat_var["FinanceTarget"] != 0, 0)

    fig = px.bar(cat_var.sort_values("Variance"), x="Category", y="Variance",
                 color="Variance", color_continuous_scale=["#f87171", "#34d399"],
                 text=cat_var["Variance"].apply(lambda x: f"₹{x/1e7:.1f}Cr"),
                 title="Variance by Category (₹ Cr)")
    st.plotly_chart(fig, width="stretch", key="fs_var_cat")

    st.markdown("")
    st.markdown("**Transaction Detail**")
    detail = df[["OrderID", "Date", "Region", "Territory", "ProductName",
                 "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue", "Profit"]].copy()
    detail["Date"] = pd.to_datetime(detail["Date"]).dt.date
    st.dataframe(
        detail.sort_values("NetRevenue", ascending=False),
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
        height=400, hide_index=True, key="fs_detail"
    )