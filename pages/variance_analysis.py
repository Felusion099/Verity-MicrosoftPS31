"""Variance Analysis page — detailed variance analysis by region, territory, product, category, and time."""

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
    df = ctx["df"]
    prev_df = ctx["prev_df"]
    
    from src.data_loader import load_finance_plan
    from src import metrics
    from src.formatting import delta_text, format_inr, format_int, format_pct
    from src.ui import empty_state, kpi_card, kpi_row, page_header
    import plotly.graph_objects as go
    import plotly.express as px

    page_header("Variance Analysis",
                "Deep-dive variance analysis by region, territory, product, category, and time.")

    df = ctx["df"]
    prev_df = ctx["prev_df"]

    if df is None or len(df) == 0:
        from src.ui import empty_state
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(ctx["df"])
    p = metrics.kpi_summary(ctx["prev_df"]) if ctx["prev_df"] is not None and len(ctx["prev_df"]) else {}

    from src.data_loader import load_finance_plan
    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(ctx["df"]["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = metrics.kpi_summary(ctx["df"])["net_revenue"]
    variance = actual - fp["FinanceTarget"].sum()
    variance_pct = (variance / fp["FinanceTarget"].sum() * 100) if fp["FinanceTarget"].sum() else 0
    achievement = (actual / fp["FinanceTarget"].sum() * 100) if fp["FinanceTarget"].sum() else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row, page_header, empty_state
    import plotly.graph_objects as go
    import plotly.express as px

    page_header("Variance Analysis",
                "Deep-dive variance analysis by region, territory, product, category, and time.")

    if df is None or len(df) == 0:
        from src.ui import empty_state
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(ctx["df"])
    p = metrics.kpi_summary(ctx["prev_df"]) if ctx["prev_df"] is not None and len(ctx["prev_df"]) else {}

    from src.data_loader import load_finance_plan
    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(ctx["df"]["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = metrics.kpi_summary(ctx["df"])["net_revenue"]
    variance = actual - fp["FinanceTarget"].sum()
    variance_pct = (variance / fp["FinanceTarget"].sum() * 100) if fp["FinanceTarget"].sum() else 0
    achievement = (actual / fp["FinanceTarget"].sum() * 100) if fp["FinanceTarget"].sum() else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row, page_header, empty_state
    import plotly.graph_objects as go
    import plotly.express as px

    page_header("Variance Analysis",
                "Deep-dive variance analysis by region, territory, product, category, and time.")

    if df is None or len(df) == 0:
        from src.ui import empty_state
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    k = metrics.kpi_summary(ctx["df"])
    p = metrics.kpi_summary(ctx["prev_df"]) if ctx["prev_df"] is not None and len(ctx["prev_df"]) else {}

    from src.data_loader import load_finance_plan
    fp = load_finance_plan()
    fp_scope = fp[fp["Date"].dt.to_period("M").isin(ctx["df"]["Date"].dt.to_period("M").unique())]

    finance_target = fp["FinanceTarget"].sum()
    finance_forecast = fp["FinanceForecast"].sum()
    expected_revenue = fp["ExpectedRevenue"].sum()

    actual = metrics.kpi_summary(ctx["df"])["net_revenue"]
    variance = actual - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (actual / finance_target * 100) if finance_target else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row, page_header, empty_state
    import plotly.graph_objects as go
    import plotly.express as px

    page_header("Variance Analysis",
                "Deep-dive variance analysis by region, territory, product, category, and time.")

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

    actual = metrics.kpi_summary(ctx["df"])["net_revenue"]
    variance = actual - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (actual / finance_target * 100) if finance_target else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row, page_header, empty_state
    import plotly.graph_objects as go
    import plotly.express as px

    page_header("Variance Analysis",
                "Deep-dive variance analysis by region, territory, product, category, and time.")

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

    actual = metrics.kpi_summary(ctx["df"])["net_revenue"]
    variance = actual - finance_target
    variance_pct = (variance / finance_target * 100) if finance_target else 0
    achievement = (actual / finance_target * 100) if finance_target else 0

    from src.formatting import delta_text, format_inr, format_pct
    from src.ui import kpi_card, kpi_row, page_header, empty_state
    import plotly.graph_objects as go
    import plotly.express as px

    page_header("Variance Analysis",
                "Deep-dive variance analysis by region, territory, product, category, and time.")

    if df is None or len(df) == 0:
        from src.ui import empty_state
        empty_state("No data matches the current filters and role scope",
                    "Try widening the date range, resetting filters, or switching the user role.")
        return

    # Overall KPIs
    kpi_row([
        {"label": "Finance Target", "value": format_inr(finance_target)},
        {"label": "Actual Revenue", "value": format_inr(actual)},
        {"label": "Variance", "value": format_inr(variance), "delta": f"{variance_pct:+.1f}%"},
        {"label": "Achievement", "value": f"{achievement:.1f}%"},
        {"label": "Forecast Accuracy", "value": f"{(1 - abs(variance)/abs(finance_target)*100):.1f}%"},
    ])

    st.markdown("")

    # Tabbed variance analysis
    tab1, tab2, tab3, tab4 = st.tabs(["By Region", "By Territory", "By Category", "By Month"])

    with tab1:
        st.markdown("**Variance by Region**")
        by_region = metrics.aggregate_by(ctx["df"], ["Region"])
        fp_region = fp.groupby("Region").agg({"FinanceTarget": "sum"}).reset_index()
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
        fig.update_layout(title="Variance vs Finance Target by Region (₹ Cr)", height=340)
        st.plotly_chart(fig, use_container_width=True, key="var_region")

    st.markdown("")

    # By Territory
    st.markdown("**Variance by Territory**")
    by_terr = metrics.aggregate_by(ctx["df"], ["Territory"])
    fp_terr = fp.groupby("Territory").agg({"FinanceTarget": "sum"}).reset_index()
    terr_var = by_region.merge(fp.groupby("Territory").agg({"FinanceTarget": "sum"}).reset_index(), on="Territory", how="left")
    terr_var["Variance"] = terr_var["NetRevenue"] - terr_var["FinanceTarget"]
    terr_var["VariancePct"] = (terr_var["Variance"] / terr_var["FinanceTarget"] * 100).where(terr_var["FinanceTarget"] != 0, 0)
    
    fig = go.Figure(go.Bar(
        x=terr_var["Territory"], y=terr_var["Variance"]/1e7,
        marker_color=["#f87171" if v < 0 else "#34d399" for v in terr_var["Variance"]],
        text=[format_inr(v) for v in terr_var["Variance"]],
        textposition="outside",
        hovertemplate="%{x}<br>Variance: %{text}<br>Target: %{customdata}<extra></extra>",
        customdata=[format_inr(v) for v in terr_var["FinanceTarget"]],
    ))
    fig.update_layout(title="Variance by Territory (₹ Cr)", height=400)
    st.plotly_chart(fig, use_container_width=True, key="var_terr")

    st.markdown("")

    # By Category
    st.markdown("**Variance by Product Category**")
    by_cat = metrics.aggregate_by(ctx["df"], ["Category"])
    fp_cat = fp.groupby("Category").agg({"FinanceTarget": "sum"}).reset_index()
    cat_var = by_cat.merge(fp_cat, on="Category", how="left")
    cat_var["Variance"] = cat_var["NetRevenue"] - cat_var["FinanceTarget"]
    cat_var["VariancePct"] = (cat_var["Variance"] / cat_var["FinanceTarget"] * 100).where(cat_var["FinanceTarget"] != 0, 0)
    
    fig = px.bar(cat_var.sort_values("Variance"), x="Category", y="Variance",
                 color="Variance", color_continuous_scale=["#f87171", "#34d399"],
                 text=cat_var["Variance"].apply(lambda x: format_inr(x)),
                 title="Variance by Category (₹ Cr)")
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True, key="var_cat")

    st.markdown("")

    # By Month
    st.markdown("**Monthly Variance Trend**")
    monthly_actual = metrics.revenue_trend(ctx["df"], "Monthly")
    fp_monthly = fp.groupby(fp["Date"].dt.to_period("M")).agg({
        "FinanceTarget": "sum",
        "FinanceForecast": "sum",
        "ExpectedRevenue": "sum"
    }).reset_index()
    fp_monthly["Label"] = fp_monthly["Date"].dt.strftime("%b %Y")

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
    st.plotly_chart(fig, use_container_width=True, key="var_monthly")