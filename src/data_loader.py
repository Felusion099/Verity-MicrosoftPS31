"""Cached data access layer: SQLite star schema -> enriched analytic DataFrame.

The enriched view is the single analytic base every page, filter, metric and
export works from. Loading is cached with @st.cache_data so interactions are
instant; "Local Data Refresh" clears the cache.
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

from src import config
from src import data_generator

FACT_QUERY = """
SELECT
    f.SalesKey, f.OrderID,
    d.DateKey, d.Date AS OrderDate, d.Day, d.Week, d.Month, d.MonthName,
    d.Quarter, d.Year, d.FiscalYear, d.FiscalQuarter,
    p.ProductKey, p.ProductID, p.ProductName, p.Category, p.Subcategory,
    c.CustomerKey, c.CustomerID, c.CustomerName, c.Segment,
    t.TerritoryKey, t.Region, t.Territory, t.Country,
    f.SalesChannel, f.UnitPrice, f.Quantity, f.GrossSales, f.DiscountRate,
    f.DiscountAmount, f.ReturnFlag, f.ReturnAmount, f.NetRevenue, f.Cost, f.Profit
FROM FACT_SALES f
JOIN DIM_DATE d      ON f.OrderDateKey = d.DateKey
JOIN DIM_PRODUCT p   ON f.ProductKey   = p.ProductKey
JOIN DIM_CUSTOMER c  ON f.CustomerKey  = c.CustomerKey
JOIN DIM_TERRITORY t ON f.TerritoryKey = t.TerritoryKey
ORDER BY d.Date, f.SalesKey
"""


@st.cache_data(show_spinner="Loading enterprise sales model...")
def load_enriched() -> pd.DataFrame:
    """Star-schema join -> one enriched fact view (cached)."""
    con = sqlite3.connect(config.DB_PATH)
    try:
        df = pd.read_sql_query(FACT_QUERY, con)
    finally:
        con.close()
    df["Date"] = pd.to_datetime(df["OrderDate"])
    return df


@st.cache_data(show_spinner=False)
def load_dims() -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(config.DB_PATH)
    try:
        return {
            "date": pd.read_sql_query("SELECT * FROM DIM_DATE ORDER BY DateKey", con),
            "product": pd.read_sql_query("SELECT * FROM DIM_PRODUCT ORDER BY ProductKey", con),
            "customer": pd.read_sql_query("SELECT * FROM DIM_CUSTOMER ORDER BY CustomerKey", con),
            "territory": pd.read_sql_query("SELECT * FROM DIM_TERRITORY ORDER BY TerritoryKey", con),
        }
    finally:
        con.close()


@st.cache_data(show_spinner=False)
def load_raw() -> pd.DataFrame:
    """Raw landing-zone CSV (with the injected data-entry issues)."""
    return pd.read_csv(config.RAW_CSV_PATH, dtype={"OrderDate": str, "ShipDate": str})


@st.cache_data(show_spinner=False)
def load_build_summary() -> dict:
    import json
    return json.loads(config.BUILD_SUMMARY_PATH.read_text())


def ensure_database() -> dict:
    """Generate the dataset on first run; otherwise return the build summary."""
    if not config.DB_PATH.exists() or not config.BUILD_SUMMARY_PATH.exists():
        return data_generator.generate_all()
    return load_build_summary()


def refresh_data() -> dict:
    """Demo refresh: clear caches and rebuild the local model deterministically."""
    st.cache_data.clear()
    return data_generator.generate_all()
