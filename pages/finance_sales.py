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
    from src.data_loader import load_finance_plan
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

    k = metrics.kpi_summary(ctx["df"])
    p = metrics.kpi_summary(ctx["prev_df"]) if ctx["prev_df"] is not None and len(ctx["prev_df"]) else {}

    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(ctx["df"]["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = k["net_revenue"]
    variance = k["net_revenue"] - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - fp["FinanceForecast"].sum()) / fp["FinanceForecast"].sum() * 100) if fp["FinanceForecast"].sum() else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row

    d_rev, c_rev = delta_text(k["net_revenue"], 0)
    d_var, c_var = delta_text(k["net_revenue"] - finance_target, 0)
    d_ach, c_ach = delta_text((k["net_revenue"] / finance_target * 100) if finance_target else 0, 0)

    from src.ui import kpi_card, kpi_row, page_header, empty_state
    from src.formatting import format_inr, format_pct, delta_text

    page_header("Finance ↔ Sales Reconciliation",
                "Finance expected X. Sales delivered Y. Variance = Z. One governed definition.")

    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(ctx["df"])
    p = metrics.kpi_summary(ctx["prev_df"]) if ctx["prev_df"] is not None and len(ctx["prev_df"]) else {}

    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(ctx["df"]["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = k["net_revenue"]
    variance = k["net_revenue"] - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - fp["FinanceForecast"].sum()) / fp["FinanceForecast"].sum() * 100) if fp["FinanceForecast"].sum() else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row

    d_rev, c_rev = delta_text(k["net_revenue"], 0)
    d_var, c_var = delta_text(k["net_revenue"] - finance_target, 0)
    d_ach, c_ach = delta_text((k["net_revenue"] / finance_target * 100) if finance_target else 0, 0)

    from src.ui import kpi_card, kpi_row, page_header, empty_state
    from src.formatting import format_inr, format_pct, delta_text

    page_header("Finance ↔ Sales Reconciliation",
                "Finance expected X. Sales delivered Y. Variance = Z. One governed definition.")

    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(df)
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}

    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(df["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = k["net_revenue"]
    variance = k["net_revenue"] - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - fp["FinanceForecast"].sum()) / fp["FinanceForecast"].sum() * 100) if fp["FinanceForecast"].sum() else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row

    d_rev, c_rev = delta_text(k["net_revenue"], 0)
    d_var, c_var = delta_text(k["net_revenue"] - finance_target, 0)
    d_ach, c_ach = delta_text((k["net_revenue"] / finance_target * 100) if finance_target else 0, 0)

    from src.ui import kpi_card, kpi_row
    from src.formatting import format_inr, format_pct, delta_text
    from src.ui import page_header, empty_state

    page_header("Finance ↔ Sales Reconciliation",
                "Finance expected X. Sales delivered Y. Variance = Z. One governed definition.")

    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(df)
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}

    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(df["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = k["net_revenue"]
    variance = k["net_revenue"] - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - fp["FinanceForecast"].sum()) / fp["FinanceForecast"].sum() * 100) if fp["FinanceForecast"].sum() else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row

    d_rev, c_rev = delta_text(k["net_revenue"], 0)
    d_var, c_var = delta_text(k["net_revenue"] - finance_target, 0)
    d_ach, c_ach = delta_text((k["net_revenue"] / finance_target * 100) if finance_target else 0, 0)

    from src.ui import kpi_card, kpi_row
    from src.formatting import format_inr, format_pct, delta_text
    from src.ui import page_header, empty_state

    page_header("Finance ↔ Sales Reconciliation",
                "Finance expected X. Sales delivered Y. Variance = Z. One governed definition.")

    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(df)
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}

    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(df["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = k["net_revenue"]
    variance = k["net_revenue"] - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - fp["FinanceForecast"].sum()) / fp["FinanceForecast"].sum() * 100) if fp["FinanceForecast"].sum() else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row

    d_rev, c_rev = delta_text(k["net_revenue"], 0)
    d_var, c_var = delta_text(k["net_revenue"] - finance_target, 0)
    d_ach, c_ach = delta_text((k["net_revenue"] / finance_target * 100) if finance_target else 0, 0)

    from src.ui import kpi_card, kpi_row
    from src.formatting import format_inr, format_pct, delta_text
    from src.ui import page_header, empty_state

    page_header("Finance ↔ Sales Reconciliation",
                "Finance expected X. Sales delivered Y. Variance = Z. One governed definition.")

    if df is None or len(df) == 0:
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(df)
    p = metrics.kpi_summary(prev_df) if prev_df is not None and len(prev_df) else {}

    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(df["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = k["net_revenue"]
    variance = k["net_revenue"] - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (k["net_revenue"] / finance_target * 100) if finance_target else 0
    forecast_accuracy = (1 - abs(k["net_revenue"] - fp["FinanceForecast"].sum()) / fp["FinanceForecast"].sum() * 100) if fp["FinanceForecast"].sum() else 0

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
    monthly_actual = metrics.revenue_trend(df, "Monthly")
    fp_monthly = fp.groupby(fp["Date"].dt.to_period("M")).agg({
        "FinanceTarget": "sum",
        "FinanceForecast": "sum",
        "ExpectedRevenue": "sum"
    }).reset_index()
    fp_monthly["Label"] = fp_monthly["Date"].dt.strftime("%b %Y")

    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_actual["Label"], y=[v / 1e7 for v in monthly_actual["NetRevenue"]],
        name="Actual Net Revenue", fill="tozeroy",
        line=dict(color="#3b82f6", width=2.4, shape="spline"),
        fillcolor="rgba(59,130,246,0.10)",
        customdata=[format_inr(v) for v in monthly_actual["NetRevenue"]],
        hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=fp_monthly["Date"].dt.strftime("%b %Y"), y=[v / 1e7 for v in fp_monthly["FinanceTarget"]],
        name="Finance Target", line=dict(color="#fbbf24", width=2, dash="dot", shape="spline"),
    ))
    fig.add_trace(go.Scatter(
        x=fp_monthly["Date"].dt.strftime("%b %Y"), y=[v / 1e7 for v in fp_monthly["FinanceForecast"]],
        name="Finance Forecast", line=dict(color="#22d3ee", width=1.6, dash="dot", shape="spline"),
    ))
    fig.update_layout(yaxis_title="Net Revenue (₹ Cr)", hovermode="x unified", height=360)
    st.plotly_chart(fig, use_container_width=True, key="fs_trend")

    st.markdown("")
    
    # Variance by Region
    st.markdown("**Variance by Region**")
    by_region = metrics.aggregate_by(df, ["Region"])
    fp_region = fp.groupby("Region").agg({
        "FinanceTarget": "sum",
        "FinanceForecast": "sum",
        "ExpectedRevenue": "sum"
    }).reset_index()
    
    var_df = by_region.merge(fp_region, on="Region", how="left")
    var_df["Variance"] = var_df["NetRevenue"] - var_df["FinanceTarget"]
    var_df["VariancePct"] = (var_df["Variance"] / var_df["FinanceTarget"] * 100).where(var_df["FinanceTarget"] != 0, 0)
    
    fig = go.Figure(go.Bar(
        x=var_df["Region"], y=var_df["Variance"]/1e7,
        marker_color=["#f87171" if v < 0 else "#34d399" for v in var_df["Variance"]],
        text=[format_inr(v) for v in var_df["Variance"]],
        textposition="outside",
        hovertemplate="%{x}<br>Variance: %{text}<br>Target: %{customdata}<extra></extra>",
        customdata=[format_inr(v) for v in var_df["FinanceTarget"]],
    ))
    fig.update_layout(title="Variance vs Finance Target by Region (₹ Cr)", height=300)
    st.plotly_chart(fig, use_container_width=True, key="fs_var_region")
    st.caption(f"Leader: {var_df.loc[var_df['Variance'].idxmax(), 'Region']} ({var_df['Variance'].max()/1e7:.1f} Cr) · Laggard: {var_df.loc[var_df['Variance'].idxmin(), 'Region']} ({var_df['Variance'].min()/1e7:.1f} Cr)")

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
    st.plotly_chart(fig, use_container_width=True, key="fs_var_cat")
    
    st.markdown("")
    
    # Drill-down table - show transactions without Finance Plan merge (OrderID vs PlanKey type mismatch)
    st.markdown("**Transaction-Level Detail**")
    detail = df[["OrderID", "Date", "Region", "Territory", "ProductName", "Category",
                 "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue"]].copy()
    
    detail_cols = ["OrderID", "Date", "Region", "Territory", "ProductName", "Category",
                   "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue"]
    avail_cols = [c for c in ["OrderID", "Date", "Region", "Territory", "ProductName", "Category",
                              "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue"] 
                  if c in df.columns]
    
    st.dataframe(
        df[["OrderID", "Date", "Region", "Territory", "ProductName", "Category",
            "Quantity", "GrossSales", "DiscountAmount", "ReturnAmount", "NetRevenue"]].sort_values("NetRevenue", ascending=False),
        use_container_width=True, height=400, hide_index=True,
        column_config={
            "OrderID": st.column_config.TextColumn("Order ID", width="small"),
            "Date": st.column_config.DateColumn("Date", width="small"),
            "Region": st.column_config.TextColumn("Region", width="small"),
            "Territory": st.column_config.TextColumn("Territory", width="small"),
            "ProductName": st.column_config.TextColumn("Product", width="large"),
            "Quantity": st.column_config.NumberColumn("Qty", width="small"),
            "GrossSales": st.column_config.NumberColumn("Gross Sales", format="₹,.0f"),
            "DiscountAmount": st.column_config.NumberColumn("Discount", format="₹,.0f"),
            "ReturnAmount": st.column_config.NumberColumn("Returns", format="₹,.0f"),
            "NetRevenue": st.column_config.NumberColumn("Net Revenue", format="₹,.0f"),
        },
        key="fs_detail"
    )