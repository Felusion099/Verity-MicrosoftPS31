"""GOVERNED METRIC LAYER — the single source of truth for every number.

Every KPI, chart, table and export in Verity flows through this
module. There is exactly ONE definition of revenue in the entire application:

    NET REVENUE = Gross Sales − Discounts − Returns

Pages must never compute revenue inline — they call these functions. The
Data Quality page verifies that the stored NetRevenue column matches this
governed formula row by row.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

NET_REVENUE_FORMULA = "Gross Sales − Discounts − Returns"

METRIC_CATALOG = [
    {"Metric": "Net Revenue", "Definition": "SUM(Gross Sales) − SUM(Discount Amount) − SUM(Return Amount)",
     "Owner": "Revenue Operations", "Status": "✓ Certified"},
    {"Metric": "Gross Revenue", "Definition": "SUM(Gross Sales)",
     "Owner": "Finance", "Status": "✓ Certified"},
    {"Metric": "Profit", "Definition": "Net Revenue − Cost",
     "Owner": "Finance", "Status": "✓ Certified"},
    {"Metric": "Profit Margin", "Definition": "Profit ÷ Net Revenue",
     "Owner": "Finance", "Status": "✓ Certified"},
    {"Metric": "Orders", "Definition": "COUNT(DISTINCT Order ID)",
     "Owner": "Sales Operations", "Status": "✓ Certified"},
    {"Metric": "Average Order Value", "Definition": "Net Revenue ÷ Orders",
     "Owner": "Revenue Operations", "Status": "✓ Certified"},
    {"Metric": "Units Sold", "Definition": "SUM(Quantity)",
     "Owner": "Supply Chain Operations", "Status": "✓ Certified"},
    {"Metric": "Return Rate", "Definition": "Returned line items ÷ Total line items",
     "Owner": "Sales Operations", "Status": "✓ Certified"},
]


def _empty(df: pd.DataFrame | None) -> bool:
    return df is None or len(df) == 0


# --------------------------------------------------------------------------
# Governed scalar metrics (single definitions, used everywhere)
# --------------------------------------------------------------------------

def net_revenue(df: pd.DataFrame | None) -> float:
    """GOVERNED METRIC — the only revenue calculation in the application."""
    if _empty(df):
        return 0.0
    return float((df["GrossSales"] - df["DiscountAmount"] - df["ReturnAmount"]).sum())


def gross_revenue(df: pd.DataFrame | None) -> float:
    if _empty(df):
        return 0.0
    return float(df["GrossSales"].sum())


def orders(df: pd.DataFrame | None) -> int:
    """GOVERNED — distinct Order IDs (an order spans multiple line items)."""
    if _empty(df):
        return 0
    return int(df["OrderID"].nunique())


def units_sold(df: pd.DataFrame | None) -> int:
    if _empty(df):
        return 0
    return int(df["Quantity"].sum())


def total_cost(df: pd.DataFrame | None) -> float:
    if _empty(df):
        return 0.0
    return float(df["Cost"].sum())


def profit(df: pd.DataFrame | None) -> float:
    """GOVERNED — Profit = Net Revenue − Cost."""
    return net_revenue(df) - total_cost(df)


def profit_margin(df: pd.DataFrame | None) -> float:
    """GOVERNED — Profit ÷ Net Revenue (as %)."""
    net = net_revenue(df)
    return (profit(df) / net * 100.0) if net > 0 else 0.0


def aov(df: pd.DataFrame | None) -> float:
    """GOVERNED — Net Revenue ÷ Orders."""
    n = orders(df)
    return (net_revenue(df) / n) if n > 0 else 0.0


def return_rate(df: pd.DataFrame | None) -> float:
    """GOVERNED — returned line items ÷ total line items (as %)."""
    if _empty(df):
        return 0.0
    return float((df["ReturnFlag"] == 1).mean() * 100.0)


def kpi_summary(df: pd.DataFrame | None) -> dict:
    """All governed KPIs for a DataFrame in one pass."""
    return {
        "net_revenue": net_revenue(df),
        "gross_revenue": gross_revenue(df),
        "orders": orders(df),
        "units_sold": units_sold(df),
        "profit": profit(df),
        "profit_margin": profit_margin(df),
        "aov": aov(df),
        "return_rate": return_rate(df),
    }


# --------------------------------------------------------------------------
# Grouped aggregation (same governed formula at every grain)
# --------------------------------------------------------------------------

def aggregate_by(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Grouped aggregation using the governed metric definitions."""
    if _empty(df):
        return pd.DataFrame(columns=keys + ["NetRevenue", "GrossSales", "DiscountAmount",
                                            "ReturnAmount", "Cost", "Profit", "Quantity",
                                            "Orders", "Lines", "Returns", "Margin", "AOV", "ReturnRate"])
    g = df.groupby(keys, sort=False).agg(
        GrossSales=("GrossSales", "sum"),
        DiscountAmount=("DiscountAmount", "sum"),
        ReturnAmount=("ReturnAmount", "sum"),
        Cost=("Cost", "sum"),
        Quantity=("Quantity", "sum"),
        Orders=("OrderID", "nunique"),
        Lines=("SalesKey", "count"),
        Returns=("ReturnFlag", "sum"),
    ).reset_index()
    # the governed formula, applied at this grain
    g["NetRevenue"] = g["GrossSales"] - g["DiscountAmount"] - g["ReturnAmount"]
    g["Profit"] = g["NetRevenue"] - g["Cost"]
    g["Margin"] = np.where(g["NetRevenue"] > 0, g["Profit"] / g["NetRevenue"] * 100.0, 0.0)
    g["AOV"] = np.where(g["Orders"] > 0, g["NetRevenue"] / g["Orders"], 0.0)
    g["ReturnRate"] = np.where(g["Lines"] > 0, g["Returns"] / g["Lines"] * 100.0, 0.0)
    return g


def revenue_trend(df: pd.DataFrame, grain: str = "Monthly") -> pd.DataFrame:
    """Net Revenue over time at Daily / Weekly / Monthly / Quarterly grain."""
    if _empty(df):
        return pd.DataFrame(columns=["Period", "Label", "NetRevenue", "Orders", "Profit", "Lines"])
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "M", "Quarterly": "Q"}[grain]
    tmp = df.assign(Period=df["Date"].dt.to_period(freq))
    agg = aggregate_by(tmp, ["Period"]).sort_values("Period")
    if grain == "Monthly":
        agg["Label"] = agg["Period"].dt.strftime("%b %Y")
    elif grain == "Quarterly":
        agg["Label"] = agg["Period"].map(lambda p: f"Q{p.quarter} {p.year}")
    elif grain == "Weekly":
        agg["Label"] = agg["Period"].dt.strftime("%d %b")
    else:
        agg["Label"] = agg["Period"].dt.strftime("%d %b")
    return agg


def window_growth_by(df: pd.DataFrame, keys: list[str], days: int = 90,
                     min_lines: int = 5) -> pd.DataFrame:
    """Growth by dimension: latest window vs preceding window of equal length."""
    if _empty(df):
        return pd.DataFrame()
    end = df["Date"].max()
    cur_start = end - pd.Timedelta(days=days - 1)
    prev_end = cur_start - pd.Timedelta(days=1)
    prev_start = prev_end - pd.Timedelta(days=days - 1)
    cur = aggregate_by(df[df["Date"] >= cur_start], keys)
    prev = aggregate_by(df[(df["Date"] >= prev_start) & (df["Date"] <= prev_end)], keys)
    keep_prev = keys + ["NetRevenue", "Orders", "Lines"]
    prev_s = prev[keep_prev].rename(columns={"NetRevenue": "PrevNetRevenue",
                                             "Orders": "PrevOrders", "Lines": "PrevLines"})
    m = cur.merge(prev_s, on=keys, how="outer")
    m[["NetRevenue", "PrevNetRevenue", "Orders", "PrevOrders", "Lines", "PrevLines"]] = \
        m[["NetRevenue", "PrevNetRevenue", "Orders", "PrevOrders", "Lines", "PrevLines"]].fillna(0)
    m["Growth"] = np.where(m["PrevNetRevenue"] > 0,
                           (m["NetRevenue"] - m["PrevNetRevenue"]) / m["PrevNetRevenue"] * 100.0,
                           np.nan)
    if min_lines:
        m = m[m["PrevLines"] >= min_lines]
    return m.sort_values("Growth", ascending=False)


def previous_period_bounds(df_filtered: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """Immediately preceding window of equal length to the filtered data."""
    if _empty(df_filtered):
        return None
    start, end = df_filtered["Date"].min(), df_filtered["Date"].max()
    length_days = max(1, (end - start).days + 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length_days - 1)
    return prev_start, prev_end
