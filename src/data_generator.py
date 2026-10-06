"""Synthetic enterprise sales data generator + ETL into a SQLite star schema.

Deterministic (seeded) so every dashboard refresh reproduces the same numbers.

Pipeline:
  1. Build dimension tables (date / product / customer / territory).
  2. Generate a realistic FACT table with seasonality, regional differences,
     product trends, segment-based discounting and returns.
  3. Write the RAW layer as CSV, deliberately injecting data-entry issues
     (duplicate rows, region typos, missing dates) — a realistic landing zone.
  4. ETL: clean the raw data (recording every repair), map names -> surrogate
     keys, and build the star schema in SQLite.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from src import config

# --------------------------------------------------------------------------
# Dimension definitions (Indian Revenue Operations scenario)
# --------------------------------------------------------------------------

CATEGORY_SPECS = {
    "Electronics":      {"share": 0.24, "margin": (0.14, 0.32), "return_rate": 0.045, "n_products": 34},
    "Home Appliances":  {"share": 0.20, "margin": (0.12, 0.28), "return_rate": 0.030, "n_products": 26},
    "Furniture":        {"share": 0.16, "margin": (0.18, 0.40), "return_rate": 0.025, "n_products": 20},
    "Office Supplies":  {"share": 0.12, "margin": (0.25, 0.50), "return_rate": 0.015, "n_products": 18},
    "Apparel":          {"share": 0.10, "margin": (0.30, 0.55), "return_rate": 0.070, "n_products": 14},
    "Sports & Fitness": {"share": 0.18, "margin": (0.20, 0.42), "return_rate": 0.035, "n_products": 16},
}

SUBCATEGORY_PRICES = {
    "Electronics": {"Laptops": (48000, 160000), "Smartphones": (16000, 115000), "Audio": (2500, 34000),
                    "Cameras": (32000, 180000), "Accessories": (800, 12000), "Tablets": (20000, 90000)},
    "Home Appliances": {"Refrigerators": (22000, 85000), "Washing Machines": (18000, 65000),
                        "Air Conditioners": (28000, 95000), "Kitchen Appliances": (3000, 30000),
                        "Microwaves": (8000, 28000)},
    "Furniture": {"Office Chairs": (9000, 65000), "Desks & Tables": (12000, 90000),
                  "Storage": (6000, 45000), "Sofas": (25000, 140000)},
    "Office Supplies": {"Stationery": (200, 3000), "Printing": (4000, 24000),
                        "Paper Products": (300, 4000), "Binders & Filing": (500, 6000)},
    "Apparel": {"Corporate Wear": (2500, 18000), "Casual Wear": (1200, 9000),
                "Footwear": (2000, 15000), "Accessories": (500, 8000)},
    "Sports & Fitness": {"Gym Equipment": (15000, 120000), "Outdoor Gear": (3000, 45000),
                         "Wearables": (5000, 40000), "Team Sports": (1500, 25000)},
}

BRANDS = ["Zenith", "Nexa", "Orbit", "Prisma", "Quanta", "Helio", "Vertex", "Astra",
          "Nova", "Kinetic", "Apex", "Solaris"]
MODEL_TOKENS = ["Pro", "Max", "Air", "Lite", "Ultra", "Prime", "Edge", "Core",
                "Elite", "Flex", "Plus", "Neo"]

REGION_SPECS = {
    "North":   {"weight": 0.24, "growth": 1.0035,
                "territories": {"Delhi NCR": 0.38, "Chandigarh": 0.18, "Jaipur": 0.24, "Lucknow": 0.20}},
    "South":   {"weight": 0.27, "growth": 1.0028,
                "territories": {"Bengaluru": 0.34, "Chennai": 0.26, "Hyderabad": 0.26, "Kochi": 0.14}},
    "West":    {"weight": 0.28, "growth": 1.0018,
                "territories": {"Mumbai": 0.36, "Pune": 0.24, "Ahmedabad": 0.22, "Nagpur": 0.18}},
    "East":    {"weight": 0.13, "growth": 0.9988,
                "territories": {"Kolkata": 0.40, "Bhubaneswar": 0.20, "Patna": 0.22, "Guwahati": 0.18}},
    "Central": {"weight": 0.08, "growth": 0.9975,
                "territories": {"Bhopal": 0.34, "Indore": 0.30, "Raipur": 0.20, "Jabalpur": 0.16}},
}

SEGMENT_SPECS = {
    "Consumer":   {"share": 0.38, "discount": 0.035,
                   "channels": {"Online": 0.45, "Retail Store": 0.33, "Direct Sales": 0.07, "Partner / Distributor": 0.15}},
    "SMB":        {"share": 0.30, "discount": 0.075,
                   "channels": {"Online": 0.30, "Retail Store": 0.20, "Direct Sales": 0.25, "Partner / Distributor": 0.25}},
    "Enterprise": {"share": 0.22, "discount": 0.125,
                   "channels": {"Online": 0.12, "Retail Store": 0.08, "Direct Sales": 0.50, "Partner / Distributor": 0.30}},
    "Government": {"share": 0.10, "discount": 0.095,
                   "channels": {"Online": 0.05, "Retail Store": 0.10, "Direct Sales": 0.55, "Partner / Distributor": 0.30}},
}
CHANNEL_DISCOUNT_UPLIFT = {"Online": 0.008, "Retail Store": 0.004, "Direct Sales": 0.0, "Partner / Distributor": 0.035}

MONTH_SEASONALITY = {1: 0.92, 2: 0.90, 3: 1.12, 4: 0.95, 5: 0.98, 6: 0.90,
                     7: 0.97, 8: 1.00, 9: 1.03, 10: 1.15, 11: 1.22, 12: 1.08}
WEEKDAY_FACTORS = {0: 1.02, 1: 0.98, 2: 0.97, 3: 1.00, 4: 1.04, 5: 0.55, 6: 0.42}

CUSTOMER_PREFIXES = ["Sharma", "Verma", "Gupta", "Mehta", "Iyer", "Reddy", "Patel", "Bose",
                     "Kapoor", "Nair", "Joshi", "Chopra", "Malhotra", "Das", "Menon", "Rao",
                     "Shah", "Bhatt", "Kulkarni", "Deshmukh"]
CUSTOMER_FORMS = ["Traders", "Enterprises", "Industries", "Technologies", "Retail Co",
                  "Solutions", "Logistics", "Group", "Distributors", "Stores"]

# Dirty-data injection volumes (raw layer) — computed, then repaired by ETL
INJECT_DUPLICATE_ROWS = 12
INJECT_REGION_TYPOS = 6
INJECT_MISSING_DATES = 8
REGION_TYPO_MAP = {"North": "Norht", "South": "Sauth", "East": "Eest",
                   "West": "Wset", "Central": "Centrl"}


# --------------------------------------------------------------------------
# Dimension builders
# --------------------------------------------------------------------------

def _build_date_dim(start: date, end: date) -> pd.DataFrame:
    days = pd.date_range(start, end, freq="D")
    df = pd.DataFrame({"Date": days})
    df["DateKey"] = df["Date"].dt.strftime("%Y%m%d").astype(int)
    df["Day"] = df["Date"].dt.day
    df["Week"] = df["Date"].dt.isocalendar().week.astype(int)
    df["Month"] = df["Date"].dt.month
    df["MonthName"] = df["Date"].dt.strftime("%b")
    df["Quarter"] = "Q" + df["Date"].dt.quarter.astype(str)
    df["Year"] = df["Date"].dt.year
    # Indian fiscal year: April–March
    df["FiscalYear"] = df["Year"] + (df["Month"] >= 4).astype(int)
    df["FiscalQuarter"] = "FQ" + ((df["Month"] - 4) % 12 // 3 + 1).astype(str)
    df["DayOfWeek"] = df["Date"].dt.dayofweek
    df["IsWeekend"] = (df["DayOfWeek"] >= 5).astype(int)
    return df


def _build_product_dim(rng: np.random.Generator) -> pd.DataFrame:
    rows, seen = [], set()
    for i, (category, spec) in enumerate(CATEGORY_SPECS.items()):
        sub_items = list(SUBCATEGORY_PRICES[category].items())
        for j in range(spec["n_products"]):
            subcat, (lo, hi) = sub_items[j % len(sub_items)]
            # unique product name
            while True:
                name = f"{rng.choice(BRANDS)} {rng.choice(MODEL_TOKENS)} {int(rng.integers(1, 999))}"
                if name not in seen:
                    seen.add(name)
                    break
            price = round(float(rng.uniform(lo, hi)) / 100) * 100
            margin = float(rng.uniform(*spec["margin"]))
            popularity = float(rng.lognormal(-0.4, 0.9))
            # product life-cycle trend: rising stars / decliners / steady
            u = rng.random()
            if u < 0.12:
                drift = float(rng.uniform(0.018, 0.032))
            elif u < 0.30:
                drift = float(rng.uniform(-0.022, -0.010))
            else:
                drift = float(rng.uniform(-0.006, 0.010))
            # ~10% of products launch mid-series
            launch = date(2024, 1, 1) + timedelta(days=int(rng.integers(0, 640))) if rng.random() < 0.10 else date(2024, 1, 1)
            rows.append({
                "ProductKey": i * 100 + j + 1,
                "ProductID": f"PRD-{i * 100 + j + 1:04d}",
                "ProductName": name,
                "Category": category,
                "Subcategory": subcat,
                "UnitPrice": price,
                "UnitCost": round(price * (1 - margin), 2),
                "PopularityWeight": popularity,
                "TrendDrift": drift,
                "LaunchDate": launch.isoformat(),
            })
    return pd.DataFrame(rows)


def _build_customer_dim(rng: np.random.Generator) -> pd.DataFrame:
    n = 3500
    names, seen = [], set()
    segments = list(SEGMENT_SPECS)
    seg_p = [SEGMENT_SPECS[s]["share"] for s in segments]
    for i in range(n):
        base = f"{rng.choice(CUSTOMER_PREFIXES)} {rng.choice(CUSTOMER_FORMS)}"
        name = base if base not in seen else f"{base} {i}"
        seen.add(name)
        rows_seg = rng.choice(segments, p=seg_p)
        names.append({"CustomerKey": i + 1, "CustomerID": f"CUST-{i + 1:05d}",
                      "CustomerName": name, "Segment": rows_seg})
    return pd.DataFrame(names)


def _build_territory_dim() -> pd.DataFrame:
    rows, key = [], 1
    for region, spec in REGION_SPECS.items():
        for territory in spec["territories"]:
            rows.append({"TerritoryKey": key, "Region": region,
                         "Territory": territory, "Country": "India"})
            key += 1
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Fact generation
# --------------------------------------------------------------------------

def _generate_fact(rng: np.random.Generator, date_dim: pd.DataFrame,
                   product_dim: pd.DataFrame, customer_dim: pd.DataFrame) -> pd.DataFrame:
    start = date_dim["Date"].min().date()
    end = date_dim["Date"].max().date()
    n_days = len(date_dim)
    # calibrate daily order volume so total rows land near the configured target
    base_daily = config.TARGET_ROW_COUNT / (n_days * 2.1)

    # deterministic month-to-month noise
    month_keys = date_dim[["Year", "Month"]].drop_duplicates().sort_values(["Year", "Month"])
    month_noise = {(int(y), int(m)): float(rng.uniform(0.93, 1.07))
                   for y, m in month_keys.itertuples(index=False)}

    region_names = list(REGION_SPECS)
    region_base = np.array([REGION_SPECS[r]["weight"] for r in region_names])
    region_growth = np.array([REGION_SPECS[r]["growth"] for r in region_names])

    # product arrays (fast lookups inside the loop)
    prod_cat_share = product_dim["Category"].map({c: s["share"] for c, s in CATEGORY_SPECS.items()})
    base_weights = (product_dim["PopularityWeight"] * prod_cat_share).to_numpy()
    drifts = product_dim["TrendDrift"].to_numpy()
    launches = pd.to_datetime(product_dim["LaunchDate"])
    p_key = product_dim["ProductKey"].to_numpy()
    p_id = product_dim["ProductID"].to_numpy()
    p_name = product_dim["ProductName"].to_numpy()
    p_cat = product_dim["Category"].to_numpy()
    p_sub = product_dim["Subcategory"].to_numpy()
    p_price = product_dim["UnitPrice"].to_numpy(dtype=float)
    p_cost = product_dim["UnitCost"].to_numpy(dtype=float)
    n_products = len(product_dim)
    cat_return = {c: s["return_rate"] for c, s in CATEGORY_SPECS.items()}

    seg_names = list(SEGMENT_SPECS)
    seg_p = [SEGMENT_SPECS[s]["share"] for s in seg_names]
    seg_keys = {s: customer_dim.loc[customer_dim["Segment"] == s, "CustomerKey"].to_numpy()
                for s in seg_names}
    seg_discount = {s: SEGMENT_SPECS[s]["discount"] for s in seg_names}
    seg_channels = {s: (list(SEGMENT_SPECS[s]["channels"]), list(SEGMENT_SPECS[s]["channels"].values()))
                    for s in seg_names}

    rows: list[dict] = []
    order_seq: dict[int, int] = {}
    sales_key = 0
    ship_opts, ship_p = [1, 2, 3, 4, 5, 7], [0.30, 0.25, 0.20, 0.10, 0.10, 0.05]
    item_opts, item_p = [1, 2, 3, 4, 5], [0.38, 0.30, 0.18, 0.10, 0.04]

    for day in date_dim.itertuples(index=False):
        day_ts = day.Date
        months_since = (day_ts.year - start.year) * 12 + (day_ts.month - start.month)
        growth = (1 + config.ANNUAL_GROWTH) ** (months_since / 12)
        lam = (base_daily * MONTH_SEASONALITY[day_ts.month] * WEEKDAY_FACTORS[day.DayOfWeek]
               * growth * month_noise[(day.Year, day.Month)])
        n_orders = int(rng.poisson(lam))

        # regional demand mix drifts over time (some regions grow faster)
        rw = region_base * region_growth ** months_since
        rw = rw / rw.sum()

        # product popularity with life-cycle drift and launch gating
        pw = base_weights * (1 + drifts) ** months_since
        pw = np.where(day_ts >= launches, pw, 0.0)
        pw = pw / pw.sum()

        for _ in range(n_orders):
            region = str(rng.choice(region_names, p=rw))
            terr = REGION_SPECS[region]["territories"]
            territory = str(rng.choice(list(terr), p=list(terr.values())))
            segment = str(rng.choice(seg_names, p=seg_p))
            ch_names, ch_p = seg_channels[segment]
            channel = str(rng.choice(ch_names, p=ch_p))
            cust_key = int(rng.choice(seg_keys[segment]))
            cust_id = f"CUST-{cust_key:05d}"

            year = day_ts.year
            order_seq[year] = order_seq.get(year, 0) + 1
            order_id = f"ORD-{year}-{order_seq[year]:05d}"
            ship_days = int(rng.choice(ship_opts, p=ship_p))

            n_items = int(rng.choice(item_opts, p=item_p))
            for _ in range(n_items):
                sales_key += 1
                idx = int(rng.choice(n_products, p=pw))
                price, qty_tier = p_price[idx], p_price[idx]
                if qty_tier < 3000:
                    qty = int(rng.integers(1, 26))
                elif qty_tier < 20000:
                    qty = int(rng.integers(1, 9))
                else:
                    qty = int(rng.integers(1, 5))
                gross = round(qty * price, 2)

                disc_rate = (seg_discount[segment] + CHANNEL_DISCOUNT_UPLIFT[channel]
                             + (0.03 if day_ts.month in (10, 11, 12) else 0.0)
                             + float(rng.normal(0, 0.02)))
                disc_rate = min(0.30, max(0.0, disc_rate))
                if rng.random() < 0.18:          # some full-price transactions
                    disc_rate = 0.0
                disc_amt = round(gross * disc_rate, 2)

                returned = rng.random() < cat_return[str(p_cat[idx])]
                ret_amt = 0.0
                if returned:
                    frac = 1.0 if rng.random() < 0.6 else 0.5
                    ret_amt = round((gross - disc_amt) * frac, 2)

                net = round(gross - disc_amt - ret_amt, 2)
                cost = round(p_cost[idx] * qty, 2)
                rows.append({
                    "SalesKey": sales_key,
                    "OrderID": order_id,
                    "OrderDate": day_ts.strftime("%Y-%m-%d"),
                    "ShipDate": (day_ts + timedelta(days=ship_days)).strftime("%Y-%m-%d"),
                    "CustomerKey": cust_key,
                    "CustomerID": cust_id,
                    "Region": region,
                    "Territory": territory,
                    "Country": "India",
                    "ProductKey": int(p_key[idx]),
                    "ProductID": str(p_id[idx]),
                    "ProductName": str(p_name[idx]),
                    "Category": str(p_cat[idx]),
                    "Subcategory": str(p_sub[idx]),
                    "SalesChannel": channel,
                    "UnitPrice": price,
                    "Quantity": qty,
                    "GrossSales": gross,
                    "DiscountRate": round(disc_rate, 4),
                    "DiscountAmount": disc_amt,
                    "ReturnFlag": 1 if returned else 0,
                    "ReturnAmount": ret_amt,
                    "NetRevenue": net,
                    "Cost": cost,
                    "Profit": round(net - cost, 2),
                })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Raw layer: write CSV with injected data-entry issues
# --------------------------------------------------------------------------

def _inject_dirty_data(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    raw = df.copy()
    # 1) classic pipeline bug: duplicate full rows (same SalesKey)
    dup_idx = rng.choice(len(raw), size=INJECT_DUPLICATE_ROWS, replace=False)
    raw = pd.concat([raw, raw.iloc[dup_idx]], ignore_index=True)
    # 2) hand-typed region labels with typos
    typo_idx = rng.choice(len(raw), size=INJECT_REGION_TYPOS, replace=False)
    raw.loc[typo_idx, "Region"] = raw.loc[typo_idx, "Region"].map(REGION_TYPO_MAP)
    # 3) blank order dates (unresolvable in ETL) and blank ship dates
    miss_idx = rng.choice(len(raw), size=INJECT_MISSING_DATES, replace=False)
    raw.loc[miss_idx, "OrderDate"] = ""
    ship_idx = rng.choice(len(raw), size=14, replace=False)
    raw.loc[ship_idx, "ShipDate"] = ""
    return raw


# --------------------------------------------------------------------------
# ETL: clean raw layer, map to surrogate keys, build the star schema
# --------------------------------------------------------------------------

def _clean_and_build_schema(raw: pd.DataFrame, dims: dict[str, pd.DataFrame]) -> dict:
    repairs: dict[str, int] = {}

    # standardize region typos ("Norht" -> "North")
    typo_fix = {v.lower(): k for k, v in REGION_TYPO_MAP.items()}
    lower = raw["Region"].astype(str).str.strip().str.lower()
    fixed = lower.isin(typo_fix)
    repairs["region_typos_standardized"] = int(fixed.sum())
    raw.loc[fixed, "Region"] = lower.loc[fixed].map(typo_fix)

    # drop rows whose order date cannot be resolved to DIM_DATE
    before = len(raw)
    dates = raw["OrderDate"].astype(str).str.strip()
    raw = raw[dates != ""].copy()
    repairs["missing_order_dates_dropped"] = before - len(raw)

    # de-duplicate the pipeline duplicates
    before = len(raw)
    raw = raw.drop_duplicates(subset=["SalesKey"], keep="first")
    repairs["duplicate_rows_removed"] = before - len(raw)

    # surrogate-key mapping
    date_key = raw["OrderDate"].str[:10].str.replace("-", "", regex=False).astype(int)
    prod_map = dims["product"].set_index("ProductName")["ProductKey"]
    cust_map = dims["customer"].set_index("CustomerID")["CustomerKey"]
    terr_map = dims["territory"].set_index(["Region", "Territory"])["TerritoryKey"]

    fact = pd.DataFrame({
        "SalesKey": raw["SalesKey"].astype(int),
        "OrderID": raw["OrderID"],
        "OrderDateKey": date_key,
        "ProductKey": raw["ProductName"].map(prod_map).astype(int),
        "CustomerKey": raw["CustomerID"].map(cust_map).astype(int),
        "TerritoryKey": pd.MultiIndex.from_arrays([raw["Region"], raw["Territory"]]).map(terr_map).astype(int),
        "SalesChannel": raw["SalesChannel"],
        "UnitPrice": raw["UnitPrice"].astype(float),
        "Quantity": raw["Quantity"].astype(int),
        "GrossSales": raw["GrossSales"].astype(float),
        "DiscountRate": raw["DiscountRate"].astype(float),
        "DiscountAmount": raw["DiscountAmount"].astype(float),
        "ReturnFlag": raw["ReturnFlag"].astype(int),
        "ReturnAmount": raw["ReturnAmount"].astype(float),
        "NetRevenue": raw["NetRevenue"].astype(float),
        "Cost": raw["Cost"].astype(float),
        "Profit": raw["Profit"].astype(float),
    })

    # write star schema
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    try:
        dims["date"].to_sql("DIM_DATE", con, if_exists="replace", index=False)
        dims["product"].to_sql("DIM_PRODUCT", con, if_exists="replace", index=False)
        dims["customer"].to_sql("DIM_CUSTOMER", con, if_exists="replace", index=False)
        dims["territory"].to_sql("DIM_TERRITORY", con, if_exists="replace", index=False)
        fact.to_sql("FACT_SALES", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_fact_date ON FACT_SALES(OrderDateKey)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_fact_product ON FACT_SALES(ProductKey)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_fact_region ON FACT_SALES(TerritoryKey)")
        con.commit()
    finally:
        con.close()

    return {"repairs": repairs,
            "fact_rows": len(fact),
            "gross_revenue": float(fact["GrossSales"].sum()),
"net_revenue": float((fact["GrossSales"] - fact["DiscountAmount"] - fact["ReturnAmount"]).sum())}


# --------------------------------------------------------------------------
# Finance Plan generation (FACT_FINANCE_PLAN)
# --------------------------------------------------------------------------

def _generate_finance_plan(rng: np.random.Generator, date_dim: pd.DataFrame,
                           product_dim: pd.DataFrame, territory_dim: pd.DataFrame) -> pd.DataFrame:
    """Generate Finance Plan/Target data (FACT_FINANCE_PLAN).
    
    Contains Finance Targets, Budgets, Forecasts, Expected Revenue
    by Date, Region, Territory, Product, Category.
    Shares the same analytical dimensions as FACT_SALES.
    """
    start = date_dim["Date"].min().date()
    end = date_dim["Date"].max().date()
    
    # Build monthly periods - generate for each month start
    month_starts = pd.date_range(start, end, freq="MS")
    
    # Territory specs with Finance Plan weights
    region_names = list(REGION_SPECS.keys())
    region_weights = np.array([config.FINANCE_PLAN_REGION_WEIGHTS.get(r, 0.0) for r in region_names])
    region_growth = np.array([REGION_SPECS[r]["growth"] for r in region_names])
    
    # Monthly factors for Finance Plan
    monthly_factors = config.FINANCE_PLAN_MONTHLY_FACTORS
    
    # Territory to region mapping
    terr_to_region = territory_dim.set_index("TerritoryKey")["Region"].to_dict()
    terr_names = territory_dim["TerritoryKey"].tolist()
    
    # Date dimension lookup
    date_to_key = date_dim.set_index("Date")["DateKey"].to_dict()
    
    # Annual targets from config
    annual_target = config.FINANCE_PLAN_ANNUAL_TARGET
    monthly_target_base = config.FINANCE_PLAN_MONTHLY_TARGET
    quarterly_target = config.FINANCE_PLAN_QUARTERLY_TARGET
    
    rows = []
    plan_key = 0
    
    # Get category list and weights
    categories = list(config.FINANCE_PLAN_CATEGORY_WEIGHTS.keys())
    cat_weights = np.array([config.FINANCE_PLAN_CATEGORY_WEIGHTS.get(c, 0.0) for c in categories])
    
    # Regional demand mix drifts over time
    region_names = list(REGION_SPECS.keys())
    region_base_weights = np.array([config.FINANCE_PLAN_REGION_WEIGHTS.get(r, 0.0) for r in region_names])
    region_growth = np.array([REGION_SPECS[r]["growth"] for r in region_names])
    
    # Generate monthly targets per region, territory, category
    for day in pd.date_range(start, end, freq="MS"):  # MS = month start
        months_since_start = (day.year - 2024) * 12 + (day.month - 1)
        growth = (1 + config.ANNUAL_GROWTH) ** (months_since_start / 12)
        
        # Monthly noise for Finance Plan
        month_noise = rng.uniform(0.95, 1.05)
        
        # Regional demand mix drifts over time
        rw = np.array([config.FINANCE_PLAN_REGION_WEIGHTS.get(r, 0.0) for r in region_names])
        rw = rw * region_growth ** months_since_start
        rw = rw / rw.sum()
        
        for region in region_names:
            terr_spec = REGION_SPECS[region]["territories"]
            territories = list(terr_spec.keys())
            terr_weights = np.array(list(terr_spec.values()))
            terr_weights = terr_weights / terr_weights.sum()
            
            for territory in territories:
                # Get territory weight within region
                terr_spec = REGION_SPECS[region]["territories"]
                territory_weight = terr_spec.get(territory, 0.0)
                
                for category in categories:
                    cat_weight = config.FINANCE_PLAN_CATEGORY_WEIGHTS.get(category, 0.0)
                    if cat_weight == 0:
                        continue
                    
                    # Base target for this combination
                    region_weight = config.FINANCE_PLAN_REGION_WEIGHTS.get(region, 0.0)
                    cat_weight = config.FINANCE_PLAN_CATEGORY_WEIGHTS.get(category, 0.0)
                    
                    if cat_weight == 0:
                        continue
                    
                    # Base monthly target for this combination
                    base_monthly = (config.FINANCE_PLAN_MONTHLY_TARGET * 
                                   config.FINANCE_PLAN_REGION_WEIGHTS.get(region, 0.0) * 
                                   config.FINANCE_PLAN_CATEGORY_WEIGHTS.get(category, 0.0))
                    
                    # Apply growth, seasonality, noise
                    monthly_factor = config.FINANCE_PLAN_MONTHLY_FACTORS.get(day.month, 1.0)
                    noise = rng.uniform(0.95, 1.05)
                    growth_factor = (1 + config.ANNUAL_GROWTH) ** (months_since_start / 12)
                    
                    monthly_target = (base_monthly * growth_factor * 
                                    monthly_factor * noise)
                    
                    # Finance Forecast - slightly different from target (Finance's view)
                    forecast = monthly_target * rng.uniform(0.98, 1.02)
                    
                    # Expected Revenue - what Finance expects to actually collect
                    expected_revenue = monthly_target * rng.uniform(0.95, 1.02)
                    
                    # Budget - typically higher than target
                    budget = monthly_target * rng.uniform(1.02, 1.08)
                    
                    date_key = int(day.strftime("%Y%m%d"))
                    
                    rows.append({
                        "PlanKey": len(rows) + 1,
                        "DateKey": int(day.strftime("%Y%m%d")),
                        "Date": day.strftime("%Y-%m-%d"),
                        "Year": day.year,
                        "Month": day.month,
                        "Quarter": f"Q{(day.month - 1) // 3 + 1}",
                        "FiscalYear": day.year + (1 if day.month >= 4 else 0),
                        "FiscalQuarter": f"FQ{((day.month - 1) % 12) // 3 + 1}",
                        "Region": region,
                        "Territory": territory,
                        "Category": category,
                        "FinanceTarget": round(monthly_target, 2),
                        "FinanceForecast": round(forecast, 2),
                        "ExpectedRevenue": round(expected_revenue, 2),
                        "Budget": round(budget, 2),
                    })
    
    return pd.DataFrame(rows)


def _build_finance_plan_dim() -> pd.DataFrame:
    """Build DIM_FINANCE_PLAN dimension table."""
    # For now, we'll use the same dimensions as sales
    # In a real scenario, this might have additional attributes
    return pd.DataFrame()


def _clean_and_build_schema(raw: pd.DataFrame, dims: dict[str, pd.DataFrame], force: bool = False) -> dict:
    """Generate the dataset and build the SQLite star schema (idempotent)."""
    if config.DB_PATH.exists() and config.BUILD_SUMMARY_PATH.exists() and not force:
        return json.loads(config.BUILD_SUMMARY_PATH.read_text())

    rng = np.random.default_rng(config.DATA_SEED)
    start = date.fromisoformat(config.DATE_START)
    end = date.fromisoformat(config.DATE_END)

    date_dim = _build_date_dim(start, end)
    product_dim = _build_product_dim(rng)
    customer_dim = _build_customer_dim(rng)
    territory_dim = _build_territory_dim()

    fact_clean = _generate_fact(rng, date_dim, product_dim, customer_dim)
    raw = _inject_dirty_data(fact_clean, rng)

    config.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_csv(config.RAW_CSV_PATH, index=False)

    dims = {"date": date_dim, "product": product_dim,
            "customer": customer_dim, "territory": territory_dim}
    
    # Build the star schema - this is the actual implementation
    # (the outer function just handles the idempotent case)
    result = _build_star_schema(rng, date_dim, product_dim, customer_dim, territory_dim, raw, dims)

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": config.DATA_SEED,
        "date_start": config.DATE_START,
        "date_end": config.DATE_END,
        "rows_raw": int(len(raw)),
        "rows_fact": result["fact_rows"],
        "orders": int(fact_clean["OrderID"].nunique()),
        "products": int(len(product_dim)),
        "customers": int(len(customer_dim)),
        "regions": int(len(REGION_SPECS)),
        "territories": int(len(territory_dim)),
        "gross_revenue": result["gross_revenue"],
        "net_revenue": result["net_revenue"],
        "repairs": result["repairs"],
    }
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.BUILD_SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    return summary


def _build_star_schema(rng: np.random.Generator, date_dim: pd.DataFrame,
                       product_dim: pd.DataFrame, customer_dim: pd.DataFrame,
                       territory_dim: pd.DataFrame, raw: pd.DataFrame,
                       dims: dict[str, pd.DataFrame]) -> dict:
    """Build the complete star schema including FACT_SALES and FACT_FINANCE_PLAN."""
    # Clean the raw data and map to surrogate keys
    typo_fix = {v.lower(): k for k, v in REGION_TYPO_MAP.items()}
    lower = raw["Region"].astype(str).str.strip().str.lower()
    fixed = lower.isin(typo_fix)
    raw.loc[fixed, "Region"] = lower.loc[fixed].map(typo_fix)

    before = len(raw)
    dates = raw["OrderDate"].astype(str).str.strip()
    raw = raw[dates != ""].copy()
    missing_dates_dropped = before - len(raw)

    before = len(raw)
    raw = raw.drop_duplicates(subset=["SalesKey"], keep="first")
    duplicate_rows_removed = before - len(raw)

    # Surrogate key mapping
    date_key = raw["OrderDate"].str[:10].str.replace("-", "", regex=False).astype(int)
    prod_map = dims["product"].set_index("ProductName")["ProductKey"]
    cust_map = dims["customer"].set_index("CustomerID")["CustomerKey"]
    terr_map = dims["territory"].set_index(["Region", "Territory"])["TerritoryKey"]

    fact_sales = pd.DataFrame({
        "SalesKey": raw["SalesKey"].astype(int),
        "OrderID": raw["OrderID"],
        "OrderDateKey": date_key,
        "ProductKey": raw["ProductName"].map(prod_map).astype(int),
        "CustomerKey": raw["CustomerID"].map(cust_map).astype(int),
        "TerritoryKey": pd.MultiIndex.from_arrays([raw["Region"], raw["Territory"]]).map(terr_map).astype(int),
        "SalesChannel": raw["SalesChannel"],
        "UnitPrice": raw["UnitPrice"].astype(float),
        "Quantity": raw["Quantity"].astype(int),
        "GrossSales": raw["GrossSales"].astype(float),
        "DiscountRate": raw["DiscountRate"].astype(float),
        "DiscountAmount": raw["DiscountAmount"].astype(float),
        "ReturnFlag": raw["ReturnFlag"].astype(int),
        "ReturnAmount": raw["ReturnAmount"].astype(float),
        "NetRevenue": raw["NetRevenue"].astype(float),
        "Cost": raw["Cost"].astype(float),
        "Profit": raw["Profit"].astype(float),
    })

    # Generate Finance Plan
    finance_plan = _generate_finance_plan(rng, dims["date"], dims["product"], dims["territory"])

    # Map Finance Plan to surrogate keys
    fp_date_key = finance_plan["DateKey"]
    fp_prod_key = finance_plan["Category"].map(
        dims["product"].groupby("Category")["ProductKey"].first()
    ).astype(int)
    fp_terr_key = finance_plan.apply(
        lambda r: dims["territory"][
            (dims["territory"]["Region"] == r["Region"]) & 
            (dims["territory"]["Territory"] == r["Territory"])
        ]["TerritoryKey"].values[0], axis=1
    )

    fact_finance = pd.DataFrame({
        "PlanKey": finance_plan["PlanKey"].astype(int),
        "DateKey": fp_date_key.astype(int),
        "ProductKey": fp_prod_key.astype(int),
        "TerritoryKey": fp_terr_key.astype(int),
        "FinanceTarget": finance_plan["FinanceTarget"].astype(float),
        "FinanceForecast": finance_plan["FinanceForecast"].astype(float),
        "ExpectedRevenue": finance_plan["ExpectedRevenue"].astype(float),
        "Budget": finance_plan["Budget"].astype(float),
    })

    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    try:
        dims["date"].to_sql("DIM_DATE", con, if_exists="replace", index=False)
        dims["product"].to_sql("DIM_PRODUCT", con, if_exists="replace", index=False)
        dims["customer"].to_sql("DIM_CUSTOMER", con, if_exists="replace", index=False)
        dims["territory"].to_sql("DIM_TERRITORY", con, if_exists="replace", index=False)
        fact_sales.to_sql("FACT_SALES", con, if_exists="replace", index=False)
        fact_finance.to_sql("FACT_FINANCE_PLAN", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_fact_date ON FACT_SALES(OrderDateKey)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_fact_product ON FACT_SALES(ProductKey)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_fact_region ON FACT_SALES(TerritoryKey)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_fp_date ON FACT_FINANCE_PLAN(DateKey)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_fp_region ON FACT_FINANCE_PLAN(TerritoryKey)")
        con.commit()
    finally:
        con.close()

    repairs = {
        "region_typos_standardized": int(fixed.sum()),
        "missing_order_dates_dropped": int(missing_dates_dropped),
        "duplicate_rows_removed": int(duplicate_rows_removed),
    }

    gross_revenue = float(fact_sales["GrossSales"].sum())
    net_revenue = float((fact_sales["GrossSales"] - fact_sales["DiscountAmount"] - fact_sales["ReturnAmount"]).sum())

    return {
        "fact_rows": len(fact_sales),
        "finance_plan_rows": len(fact_finance),
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "repairs": repairs,
    }


def generate_all(force: bool = False) -> dict:
    """Generate the dataset and build the SQLite star schema (idempotent)."""
    if config.DB_PATH.exists() and config.BUILD_SUMMARY_PATH.exists() and not force:
        return json.loads(config.BUILD_SUMMARY_PATH.read_text())

    rng = np.random.default_rng(config.DATA_SEED)
    start = date.fromisoformat(config.DATE_START)
    end = date.fromisoformat(config.DATE_END)

    date_dim = _build_date_dim(start, end)
    product_dim = _build_product_dim(rng)
    customer_dim = _build_customer_dim(rng)
    territory_dim = _build_territory_dim()

    fact_clean = _generate_fact(rng, date_dim, product_dim, customer_dim)
    raw = _inject_dirty_data(fact_clean, rng)

    config.DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_csv(config.RAW_CSV_PATH, index=False)

    dims = {"date": date_dim, "product": product_dim,
            "customer": customer_dim, "territory": territory_dim}

    result = _clean_and_build_schema(raw, dims, force=force)

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": config.DATA_SEED,
        "date_start": config.DATE_START,
        "date_end": config.DATE_END,
        "rows_raw": int(len(raw)),
        "fact_rows": result["rows_fact"],
        "finance_plan_rows": result.get("finance_plan_rows", 0),
        "orders": int(fact_clean["OrderID"].nunique()),
        "products": int(len(product_dim)),
        "customers": int(len(customer_dim)),
        "regions": int(len(REGION_SPECS)),
        "territories": int(len(territory_dim)),
        "gross_revenue": result["gross_revenue"],
        "net_revenue": result["net_revenue"],
        "repairs": result["repairs"],
    }
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.BUILD_SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    summary = generate_all(force=True)
    print(json.dumps(summary, indent=2))
