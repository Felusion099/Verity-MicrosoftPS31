"""Verification engine — statistical anomaly detection for silent human error.

The Data Quality page's rule-based checks catch STRUCTURAL errors (typos,
duplicates, missing dates). This module catches the SILENT ones that rules
can't see: a month where revenue swings far outside its normal range, a
discount rate that drifted, a return rate that spiked, a product margin that
collapsed. Every finding is computed from the data with a plain-language
explanation and a recommended action — no black box, no hallucination.

In production this engine would run continuously (data observability); here
it runs on every Data Quality page load.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import metrics
from src.formatting import format_inr, format_int, format_pct

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _flags(series: pd.Series, threshold: float = 2.0) -> pd.Series:
    """True where a value sits beyond `threshold` standard deviations of the mean."""
    if len(series) < 4:
        return pd.Series(False, index=series.index)
    std = series.std()
    if not std or pd.isna(std) or std == 0:
        return pd.Series(False, index=series.index)
    return (series - series.mean()).abs() > threshold * std


def _z(series: pd.Series, value: float) -> float:
    std = series.std()
    return abs(value - series.mean()) / std if std and not pd.isna(std) else 0.0


def scan(df: pd.DataFrame, max_findings: int = 8) -> list[dict]:
    """Run all statistical checks. Returns findings sorted by severity."""
    findings: list[dict] = []
    if df is None or len(df) == 0:
        return findings

    monthly = metrics.revenue_trend(df, "Monthly")
    if len(monthly) >= 4:
        findings += _revenue_swings(monthly)
        findings += _volume_anomalies(monthly)
        findings += _yoy_regressions(monthly)

    findings += _discount_drift(df)
    findings += _return_spikes(df)
    findings += _margin_outliers(df)

    findings.sort(key=lambda f: (SEVERITY_ORDER.get(f["severity"], 3), f["title"]))
    return findings[:max_findings]


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def _revenue_swings(monthly: pd.DataFrame) -> list[dict]:
    """Months where MoM revenue movement is beyond ±2σ of historical swings."""
    net = monthly["NetRevenue"]
    mom = net.pct_change().mul(100).dropna()
    flagged = _flags(mom, 2.0)
    swing = mom.std()
    out = []
    for idx in mom.index[flagged]:
        row, prev = monthly.loc[idx], monthly.loc[idx - 1]
        change = mom.loc[idx]
        out.append({
            "severity": "high" if _z(mom, change) >= 3 else "medium",
            "title": f"Revenue swing: {row['Label']}",
            "finding": f"Net Revenue moved {change:+.1f}% vs {prev['Label']} "
                       f"({format_inr(prev['NetRevenue'])} → {format_inr(row['NetRevenue'])}), "
                       f"while normal month-to-month movement is ±{swing:.1f}%.",
            "action": "Confirm with Sales whether this is seasonal demand or an error in the statements.",
        })
    return out


def _volume_anomalies(monthly: pd.DataFrame) -> list[dict]:
    """Months where order volume is beyond ±2σ of the historical pattern."""
    orders = monthly["Orders"].astype(float)
    flagged = _flags(orders, 2.0)
    out = []
    for idx in orders.index[flagged]:
        row = monthly.loc[idx]
        out.append({
            "severity": "medium",
            "title": f"Order volume anomaly: {row['Label']}",
            "finding": f"{format_int(row['Orders'])} orders vs a typical month of "
                       f"{format_int(orders.mean())} (±{orders.std():.0f}).",
            "action": "Check for duplicate uploads, missing feeds, or a genuine demand event.",
        })
    return out


def _yoy_regressions(monthly: pd.DataFrame) -> list[dict]:
    """Months where revenue regressed vs the same month last year by >15%."""
    net = monthly.set_index("Period")["NetRevenue"]
    out = []
    for period, value in net.items():
        prev_year = period - 12  # same month, one year earlier (monthly periods)
        if prev_year in net.index and net.loc[prev_year] > 0:
            yoy = (value - net.loc[prev_year]) / net.loc[prev_year] * 100
            if yoy < -15:
                out.append({
                    "severity": "high",
                    "title": f"Revenue regression: {period.strftime('%b %Y')}",
                    "finding": f"Down {abs(yoy):.1f}% vs {prev_year.strftime('%b %Y')} "
                               f"({format_inr(net.loc[prev_year])} → {format_inr(value)}).",
                    "action": "Rule out data gaps or territory re-mapping before treating it as real decline.",
                })
    return out


def _discount_drift(df: pd.DataFrame) -> list[dict]:
    """Months where the average discount rate drifted beyond +2σ."""
    disc = df.groupby(df["Date"].dt.to_period("M"))["DiscountRate"].mean().mul(100)
    flagged = _flags(disc, 2.0)
    out = []
    for period in disc.index[flagged]:
        value = disc.loc[period]
        out.append({
            "severity": "medium",
            "title": f"Discount drift: {period.strftime('%b %Y')}",
            "finding": f"Average discount rate hit {value:.1f}% vs a typical {disc.mean():.1f}% "
                       f"(±{disc.std():.1f}%).",
            "action": "Verify whether a sales approval or an entry error moved discounting.",
        })
    return out


def _return_spikes(df: pd.DataFrame) -> list[dict]:
    """Months where the return rate spiked beyond +2σ."""
    ret = df.groupby(df["Date"].dt.to_period("M"))["ReturnFlag"].mean().mul(100)
    flagged = _flags(ret, 2.0)
    out = []
    for period in ret.index[flagged]:
        value = ret.loc[period]
        out.append({
            "severity": "medium",
            "title": f"Return-rate spike: {period.strftime('%b %Y')}",
            "finding": f"Return rate hit {value:.1f}% vs a typical {ret.mean():.1f}% (±{ret.std():.1f}%).",
            "action": "Check for a defective batch, a returns-processing error, or a policy change.",
        })
    return out


def _margin_outliers(df: pd.DataFrame, min_lines: int = 20) -> list[dict]:
    """Products whose margin sits far below the portfolio — possible cost/price entry error."""
    by_prod = metrics.aggregate_by(df, ["ProductName"])
    pool = by_prod[by_prod["Lines"] >= min_lines]
    if len(pool) < 5:
        return []
    low = pool[pool["Margin"] < pool["Margin"].mean() - 2 * pool["Margin"].std()]
    out = []
    for _, row in low.sort_values("Margin").iterrows():
        out.append({
            "severity": "high",
            "title": f"Margin outlier: {row['ProductName']}",
            "finding": f"Margin of {row['Margin']:.1f}% vs portfolio average of "
                       f"{pool['Margin'].mean():.1f}% on {format_int(row['Lines'])} line items.",
            "action": "Verify the product's cost price — a wrong cost entry silently erodes profit.",
        })
    return out
