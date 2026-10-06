"""Validation: governed metric consistency, filters, RLS, formatting."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
import pandas as pd

from src import config, metrics, filters, rls, formatting

# ---- load via star-schema join
con = sqlite3.connect(config.DB_PATH)
q = """SELECT f.SalesKey, f.OrderID, d.Date AS OrderDate, d.DateKey, d.MonthName, d.Quarter, d.Year,
p.ProductName, p.Category, c.CustomerID, c.Segment, t.Region, t.Territory, t.Country,
f.SalesChannel, f.Quantity, f.GrossSales, f.DiscountRate, f.DiscountAmount, f.ReturnFlag,
f.ReturnAmount, f.NetRevenue, f.Cost, f.Profit
FROM FACT_SALES f
JOIN DIM_DATE d ON f.OrderDateKey = d.DateKey
JOIN DIM_PRODUCT p ON f.ProductKey = p.ProductKey
JOIN DIM_CUSTOMER c ON f.CustomerKey = c.CustomerKey
JOIN DIM_TERRITORY t ON f.TerritoryKey = t.TerritoryKey"""
df = pd.read_sql_query(q, con)
con.close()
df["Date"] = pd.to_datetime(df["OrderDate"])

# ---- 1. governed consistency: components == stored column == aggregates
way1 = metrics.net_revenue(df)
way2 = float(df["NetRevenue"].sum())
by_region = metrics.aggregate_by(df, ["Region"])
way3 = float(by_region["NetRevenue"].sum())
assert abs(way1 - way2) < 0.01, f"component {way1} != stored {way2}"
assert abs(way1 - way3) < 0.01, f"component {way1} != aggregates {way3}"
print(f"1. CONSISTENCY OK: net revenue = {formatting.format_inr(way1)} (3 ways identical)")

# ---- 2. governed metric sanity: AOV, margin, profit
k = metrics.kpi_summary(df)
assert abs(k["profit"] - (k["net_revenue"] - df["Cost"].sum())) < 0.01
assert abs(k["aov"] - k["net_revenue"] / k["orders"]) < 0.01
print(f"2. KPI OK: profit={formatting.format_inr(k['profit'])}, aov={formatting.format_inr(k['aov'])}, margin={k['profit_margin']:.1f}%")

# ---- 3. filters: year filter + region filter compose
spec = filters.FilterSpec(years=[2026])
f1 = filters.apply_filters(df, spec)
assert f1["Year"].eq(2026).all()
spec2 = filters.FilterSpec(years=[2026], regions=["North"])
f2 = filters.apply_filters(df, spec2)
assert f2["Region"].eq("North").all() and f2["Year"].eq(2026).all()
spec3 = filters.FilterSpec(years=[2026], regions=["North"], categories=["Electronics"])
f3 = filters.apply_filters(df, spec3)
assert f3["Category"].eq("Electronics").all()
print(f"3. FILTERS OK: 2026 -> {len(f1):,} rows | North -> {len(f2):,} | North+Electronics -> {len(f3):,}")

# ---- 4. previous period: same length immediately before
pp = filters.previous_period_spec(spec2, f2)
assert pp is not None
p2 = filters.apply_filters(df, pp)
assert len(p2) > 0
assert p2["Date"].max() < f2["Date"].min()
print(f"4. PREV PERIOD OK: {p2['Date'].min().date()} .. {p2['Date'].max().date()}")

# ---- 5. RLS: role restricts regions; exports respect it
exec_df = rls.apply_rls(df, "Executive")
north_df = rls.apply_rls(df, "North Sales Manager")
south_df = rls.apply_rls(df, "South Sales Manager")
assert north_df["Region"].eq("North").all() and south_df["Region"].eq("South").all()
assert len(exec_df) == len(df)
nf = filters.apply_filters(north_df, filters.FilterSpec(years=[2026]))
assert nf["Region"].eq("North").all()
print(f"5. RLS OK: exec={len(exec_df):,}, north={len(north_df):,}, south={len(south_df):,}")

# ---- 6. formatting
assert formatting.format_inr(482_000_000) == "₹48.2 Cr"
assert formatting.format_inr(740_000) == "₹7.4 L"
assert formatting.format_inr(84_200) == "₹84,200"
assert formatting.format_int(12_84_540) == "12,84,540"
print("6. FORMATTING OK:", formatting.format_inr(482_000_000), formatting.format_inr(740_000), formatting.format_inr(84_200))

# ---- 7. trend grains
for grain in ("Daily", "Weekly", "Monthly", "Quarterly"):
    t = metrics.revenue_trend(f1, grain)
    assert len(t) > 0
print("7. TREND OK: all 4 grains aggregate")

# ---- 8. empty states safe
assert metrics.net_revenue(df.iloc[0:0]) == 0.0
assert metrics.kpi_summary(df.iloc[0:0])["orders"] == 0
assert filters.apply_filters(df, filters.FilterSpec(years=[1999])).empty
print("8. EMPTY SAFE OK")

print("\nALL VALIDATIONS PASSED")
