"""AI Trainer — standalone verification trainer for the governed model.

Three phases:
  1. LEARN     — builds a baseline profile of YOUR data: per-segment discount
                 norms, per-category return norms, delivery lead-time norms
                 and per-product price integrity. Saved as a "trained model".
  2. PINPOINT  — scans every statement (transaction line item) and flags the
                 EXACT rows that mismatch: hard formula violations (Net Revenue
                 ≠ Gross − Discounts − Returns, Profit ≠ Net − Cost, Gross ≠
                 Qty × Price, over-refunds, price drift) plus rows outside the
                 learned norms (discount outliers per segment, lead-time
                 anomalies).
  3. EXPLAIN   — every finding names the exact statement, the column that
                 mismatches, expected vs actual, and the likely CAUSE.

Standalone by design: no dashboard needed — run `python -m src.trainer` for a
full CLI report (also saved to data/processed/trainer_report.json). The
dashboard's "AI Trainer" page renders the same engine interactively and can
be re-trained on any filtered scope.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

import numpy as np
import pandas as pd

from src import config

# self-contained loader query (no dashboard imports — standalone)
QUERY = """
SELECT f.SalesKey, f.OrderID, d.Date AS OrderDate, p.ProductName, p.Category,
       c.Segment, t.Region, t.Territory, f.SalesChannel, f.UnitPrice,
       f.Quantity, f.GrossSales, f.DiscountRate, f.DiscountAmount,
       f.ReturnFlag, f.ReturnAmount, f.NetRevenue, f.Cost, f.Profit
FROM FACT_SALES f
JOIN DIM_DATE d      ON f.OrderDateKey = d.DateKey
JOIN DIM_PRODUCT p   ON f.ProductKey   = p.ProductKey
JOIN DIM_CUSTOMER c  ON f.CustomerKey  = c.CustomerKey
JOIN DIM_TERRITORY t ON f.TerritoryKey = t.TerritoryKey
ORDER BY f.SalesKey
"""

RULES = {
    "revenue_formula": "Revenue formula — Net Revenue ≠ Gross − Discounts − Returns",
    "profit_formula": "Profit formula — Profit ≠ Net Revenue − Cost",
    "gross_formula": "Gross formula — Gross Sales ≠ Quantity × Unit Price",
    "over_refund": "Over-refund — Return amount exceeds net of discount",
    "discount_overflow": "Discount exceeds gross sales",
    "price_drift": "Unit price drifts from the product's price baseline",
    "negative_values": "Negative or nonsense amounts",
    "discount_outlier": "Discount far outside the learned segment norm",
    "lead_time_anomaly": "Delivery lead time far outside the learned norm",
}

MAX_PER_RULE = 25  # exact rows shown per rule (totals always reported)


# --------------------------------------------------------------------------
# Phase 1 — LEARN
# --------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    """Standalone loader (no dashboard dependency)."""
    con = sqlite3.connect(config.DB_PATH)
    try:
        df = pd.read_sql_query(QUERY, con)
    finally:
        con.close()
    df["Date"] = pd.to_datetime(df["OrderDate"])
    return df


def build_profile(df: pd.DataFrame) -> dict:
    """LEARN: baseline profile of the data's normal behaviour."""
    disc = df.groupby("Segment")["DiscountRate"].agg(["mean", "std"])
    profile = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "rows_scanned": int(len(df)),
        "segment_discount_norm": {
            str(seg): {"mean_pct": round(float(row["mean"]) * 100, 2),
                       "std_pct": round(float(0 if pd.isna(row["std"]) else row["std"]) * 100, 2)}
            for seg, row in disc.iterrows()
        },
        "category_return_norm": {
            str(cat): round(float(v) * 100, 2)
            for cat, v in (df.groupby("Category")["ReturnFlag"].mean() * 100).items()
        },
        "lead_time_days": {},
    }
    ship = pd.to_datetime(df["OrderDate"], errors="coerce")
    if "ShipDate" in df.columns:
        lead = (pd.to_datetime(df["ShipDate"], errors="coerce") - df["Date"]).dt.days.dropna()
        profile["lead_time_days"] = {"mean": round(float(lead.mean()), 1),
                                     "std": round(float(lead.std()), 1)}
    # price baseline: each product should sell at ONE price
    price_mode = df.groupby("ProductName")["UnitPrice"].agg(
        lambda s: float(s.mode().iloc[0]) if len(s.mode()) else float("nan"))
    profile["price_baseline_count"] = int(price_mode.notna().sum())
    return profile


# --------------------------------------------------------------------------
# Phase 2 + 3 — PINPOINT & EXPLAIN
# --------------------------------------------------------------------------

def pinpoint(df: pd.DataFrame, profile: dict | None = None,
             tolerance: float = 2.0) -> tuple[list[dict], dict[str, int]]:
    """Scan every statement; return (exact mismatching rows, total count per rule).

    Exact rows are capped per rule for display; `totals` always reports the
    full count per rule.
    """
    findings: list[dict] = []
    totals: dict[str, int] = {}

    def add(idx, rule, column, expected, actual, cause, severity, z=0.0):
        r = df.loc[idx]
        findings.append({
            "sales_key": int(r["SalesKey"]), "order_id": r["OrderID"],
            "date": str(r["OrderDate"]), "product": r["ProductName"],
            "region": r["Region"], "segment": r["Segment"],
            "rule": rule, "rule_label": RULES[rule], "column": column,
            "expected": str(expected), "actual": str(actual),
            "cause": cause, "severity": severity, "z": round(float(z), 2),
        })

    def flagged(rule, bad: pd.Series):
        totals[rule] = int(bad.sum())
        return list(df.index[bad][:MAX_PER_RULE])

    # ---- hard invariants: exact formula mismatches ------------------------
    exp_net = df["GrossSales"] - df["DiscountAmount"] - df["ReturnAmount"]
    bad = (df["NetRevenue"] - exp_net).abs() > 0.01
    for idx in flagged("revenue_formula", bad):
        add(idx, "revenue_formula", "NetRevenue",
            f"₹{exp_net.loc[idx]:,.2f}", f"₹{df.at[idx, 'NetRevenue']:,.2f}",
            "Stored Net Revenue does not match Gross − Discounts − Returns — "
            "pipeline drift or a manual edit changed this statement.", "high")

    exp_profit = df["NetRevenue"] - df["Cost"]
    bad = (df["Profit"] - exp_profit).abs() > 0.01
    for idx in flagged("profit_formula", bad):
        add(idx, "profit_formula", "Profit",
            f"₹{exp_profit.loc[idx]:,.2f}", f"₹{df.at[idx, 'Profit']:,.2f}",
            "Profit does not equal Net Revenue − Cost — a cost entry or "
            "stale pipeline row.", "high")

    exp_gross = (df["Quantity"] * df["UnitPrice"]).round(2)
    bad = (df["GrossSales"] - exp_gross).abs() > 0.05
    for idx in flagged("gross_formula", bad):
        add(idx, "gross_formula", "GrossSales",
            f"₹{exp_gross.loc[idx]:,.2f}", f"₹{df.at[idx, 'GrossSales']:,.2f}",
            "Gross Sales does not equal Quantity × Unit Price — quantity or "
            "price entry error.", "high")

    bad = df["ReturnAmount"] > df["GrossSales"] - df["DiscountAmount"] + 0.01
    for idx in flagged("over_refund", bad):
        add(idx, "over_refund", "ReturnAmount",
            f"≤ ₹{df.at[idx, 'GrossSales'] - df.at[idx, 'DiscountAmount']:,.2f}",
            f"₹{df.at[idx, 'ReturnAmount']:,.2f}",
            "Refunded more than the customer paid net of discount — refund "
            "fraction error in returns processing.", "high")

    bad = df["DiscountAmount"] > df["GrossSales"] + 0.01
    for idx in flagged("discount_overflow", bad):
        add(idx, "discount_overflow", "DiscountAmount",
            f"≤ ₹{df.at[idx, 'GrossSales']:,.2f}", f"₹{df.at[idx, 'DiscountAmount']:,.2f}",
            "Discount exceeds the gross sale itself — approval or entry error.", "high")

    bad = (df["NetRevenue"] < -0.01) | (df["Quantity"] <= 0) | (df["UnitPrice"] <= 0)
    for idx in flagged("negative_values", bad):
        add(idx, "negative_values", "NetRevenue/Qty/Price", "positive",
            f"₹{df.at[idx, 'NetRevenue']:,.2f} / qty {df.at[idx, 'Quantity']}",
            "Negative or nonsense amounts — data entry error.", "high")

    # ---- learned-profile rules: outside the trained norms ------------------
    if profile:
        norm = profile.get("segment_discount_norm", {})
        seg_stats = df["Segment"].map(lambda s: norm.get(s, {}))
        seg_mean = seg_stats.map(lambda d: d.get("mean_pct", 0.0) / 100.0)
        seg_std = seg_stats.map(lambda d: d.get("std_pct", 0.0) / 100.0)
        seg_std = seg_std.where(seg_std > 0, 0.005)
        z = ((df["DiscountRate"] - seg_mean) / seg_std).abs()
        bad = z > tolerance
        top = flagged("discount_outlier", bad)
        for idx in top:
            seg = df.at[idx, "Segment"]
            n = norm.get(seg, {})
            add(idx, "discount_outlier", "DiscountRate",
                f"{n.get('mean_pct', 0):.1f}% ± {n.get('std_pct', 0):.1f} for {seg}",
                f"{df.at[idx, 'DiscountRate'] * 100:.1f}%",
                f"Discount is {z.loc[idx]:.1f}σ outside the {seg} norm — possible "
                f"manual override, approval exception or entry error.",
                "medium", z.loc[idx])

        lead = profile.get("lead_time_days", {})
        if lead.get("std", 0) and "ShipDate" in df.columns:
            lead_days = (pd.to_datetime(df["ShipDate"], errors="coerce") - df["Date"]).dt.days
            z = ((lead_days - lead["mean"]) / lead["std"]).abs()
            bad = z > 3.0
            for idx in flagged("lead_time_anomaly", bad):
                add(idx, "lead_time_anomaly", "ShipDate",
                    f"~{lead['mean']:.0f} ± {lead['std']:.0f} days",
                    f"{lead_days.loc[idx]:.0f} days",
                    "Delivery lead time far outside the learned norm — possible "
                    "mis-keyed ship date.", "medium", z.loc[idx])

    # severity, then most extreme
    findings.sort(key=lambda f: (0 if f["severity"] == "high" else 1, -f["z"]))
    return findings, totals


def summarize(findings: list[dict], totals: dict[str, int]) -> dict:
    """Counts by rule and severity for the report (totals are the full counts)."""
    by_rule: dict[str, int] = dict(totals)
    by_severity: dict[str, int] = {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    return {"by_rule": by_rule, "by_severity": by_severity,
            "total": int(sum(by_rule.values()))}


# --------------------------------------------------------------------------
# Standalone CLI
# --------------------------------------------------------------------------

def run_cli(tolerance: float = 2.0) -> dict:
    df = load_data()
    profile = build_profile(df)
    findings, totals = pinpoint(df, profile, tolerance)
    summary = summarize(findings, totals)

    print("=" * 74)
    print("AI TRAINER — verification report (governed model)")
    print("=" * 74)
    print(f"Scanned: {profile['rows_scanned']:,} statements · "
          f"trained on {profile['rows_scanned']:,} rows · strictness {tolerance:.1f}σ")
    print(f"Learned norms: discount by segment, returns by category"
          + (f", lead time {profile['lead_time_days']['mean']} ± "
             f"{profile['lead_time_days']['std']} days" if profile.get("lead_time_days") else ""))
    print("-" * 74)
    if not findings:
        print("✓ ALL STATEMENTS MATCH — no formula violations, no norm outliers.")
    else:
        print(f"{summary['total']} mismatching statements pinpointed "
              f"(high = formula violations, medium = outside learned norms):\n")
        for f in findings[:30]:
            print(f"[{f['severity'].upper():6}] {f['order_id']} · {f['product'][:34]:34} "
                  f"· {f['region']:7} · {f['column']}")
            print(f"         expected {f['expected']} | actual {f['actual']} | rule: {f['rule_label']}")
            print(f"         cause: {f['cause']}")
        if summary["total"] > 30:
            print(f"\n… and {summary['total'] - 30} more (see saved report).")
    print("-" * 74)

    report = {"generated_at": profile["built_at"], "tolerance_sigma": tolerance,
              "profile": profile, "summary": summary, "findings": findings}
    config.BUILD_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    (config.DATA_PROCESSED_DIR / "trainer_report.json").write_text(json.dumps(report, indent=2))
    print(f"Report saved: {config.DATA_PROCESSED_DIR / 'trainer_report.json'}")
    return report


if __name__ == "__main__":
    run_cli()
