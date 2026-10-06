"""Global filter system — declarative filter spec applied identically everywhere.

The sidebar builds a FilterSpec; `apply_filters` turns it into one pandas mask
used by every page, chart, KPI and export, so filtering can never diverge.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

import pandas as pd
import streamlit as st

from src import metrics


@dataclass
class FilterSpec:
    start: date | None = None
    end: date | None = None
    custom_range: bool = False
    years: list = field(default_factory=list)
    quarters: list = field(default_factory=list)
    months: list = field(default_factory=list)
    regions: list = field(default_factory=list)
    territories: list = field(default_factory=list)
    countries: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    products: list = field(default_factory=list)
    segments: list = field(default_factory=list)
    channels: list = field(default_factory=list)


def _mask(df: pd.DataFrame, col: str, values: list) -> pd.Series:
    if not values:
        return pd.Series(True, index=df.index)
    return df[col].isin(values)


def apply_filters(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    """Apply the filter spec as ONE consistent mask (dates + dimensions)."""
    if df is None or len(df) == 0:
        return df
    mask = pd.Series(True, index=df.index)
    if spec.custom_range and spec.start and spec.end:
        d = df["Date"].dt.date
        mask &= (d >= spec.start) & (d <= spec.end)
    else:
        mask &= _mask(df, "Year", spec.years)
        mask &= _mask(df, "Quarter", spec.quarters)
        mask &= _mask(df, "MonthName", spec.months)
    mask &= _mask(df, "Region", spec.regions)
    mask &= _mask(df, "Territory", spec.territories)
    mask &= _mask(df, "Country", spec.countries)
    mask &= _mask(df, "Category", spec.categories)
    mask &= _mask(df, "ProductName", spec.products)
    mask &= _mask(df, "Segment", spec.segments)
    mask &= _mask(df, "SalesChannel", spec.channels)
    return df[mask]


def previous_period_spec(spec: FilterSpec, df_filtered: pd.DataFrame) -> FilterSpec | None:
    """Same dimension filters, shifted to the immediately preceding window."""
    bounds = metrics.previous_period_bounds(df_filtered)
    if bounds is None:
        return None
    prev_start, prev_end = bounds
    return replace(spec, start=prev_start.date(), end=prev_end.date(),
                   custom_range=True, years=[], quarters=[], months=[])


# --------------------------------------------------------------------------
# Sidebar filter UI
# --------------------------------------------------------------------------

_FILTER_KEYS = ["f_years", "f_quarters", "f_months", "f_regions", "f_territories",
                "f_countries", "f_categories", "f_products", "f_segments",
                "f_channels", "f_custom_range", "f_daterange"]


def reset_filters() -> None:
    for key in _FILTER_KEYS:
        st.session_state.pop(key, None)


def render_sidebar_filters(rls_df: pd.DataFrame) -> FilterSpec:
    """Build the FilterSpec from sidebar widgets (options respect the role scope)."""
    ss = st.session_state
    # when the RBAC role changes, options change -> reset stale selections
    if ss.get("_last_role") != ss.get("role"):
        reset_filters()
        ss["_last_role"] = ss.get("role")

    all_years = sorted(rls_df["Year"].unique().tolist(), reverse=True)
    all_quarters = ["Q1", "Q2", "Q3", "Q4"]
    all_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    regions = sorted(rls_df["Region"].unique().tolist())
    countries = sorted(rls_df["Country"].unique().tolist())
    categories = sorted(rls_df["Category"].unique().tolist())
    segments = sorted(rls_df["Segment"].unique().tolist())
    channels = sorted(rls_df["SalesChannel"].unique().tolist())

    st.markdown("**Filters**")

    sel_regions = st.multiselect("Region", regions, key="f_regions")
    # dependent filter: territories inside the selected regions only
    terr_pool = rls_df
    if sel_regions:
        terr_pool = rls_df[rls_df["Region"].isin(sel_regions)]
    territories = sorted(terr_pool["Territory"].unique().tolist())
    st.multiselect("Territory", territories, key="f_territories")
    st.multiselect("Country", countries, key="f_countries")

    st.multiselect("Product Category", categories, key="f_categories")
    # dependent filter: products inside the selected categories only
    prod_pool = rls_df
    if ss.get("f_categories"):
        prod_pool = rls_df[rls_df["Category"].isin(ss["f_categories"])]
    products = sorted(prod_pool["ProductName"].unique().tolist())
    st.multiselect("Product", products, key="f_products")

    st.multiselect("Customer Segment", segments, key="f_segments")
    st.multiselect("Sales Channel", channels, key="f_channels")

    st.markdown("")
    # presentation-friendly default: current (latest) year preselected
    if "f_years" not in ss:
        ss.f_years = [all_years[0]]
    st.multiselect("Year", all_years, key="f_years",
                   help="Defaults to the current year for a strong first impression")
    st.multiselect("Quarter", all_quarters, key="f_quarters")
    st.multiselect("Month", all_months, key="f_months")

    with st.expander("Custom date range (overrides Year / Quarter / Month)"):
        st.toggle("Use custom date range", key="f_custom_range")
        lo = rls_df["Date"].min().date()
        hi = rls_df["Date"].max().date()
        rng = st.date_input("Date range", value=(lo, hi), min_value=lo, max_value=hi,
                            key="f_daterange")

    if st.button("↺ Reset filters", width="stretch"):
        reset_filters()
        st.rerun()

    sel_territories = ss.get("f_territories") or []
    sel_countries = ss.get("f_countries") or []
    sel_categories = ss.get("f_categories") or []
    sel_products = ss.get("f_products") or []
    sel_segments = ss.get("f_segments") or []
    sel_channels = ss.get("f_channels") or []
    sel_years = ss.get("f_years") or []
    sel_quarters = ss.get("f_quarters") or []
    sel_months = ss.get("f_months") or []
    custom = bool(ss.get("f_custom_range")) and isinstance(rng, tuple) and len(rng) == 2

    start, end = (None, None)
    if custom:
        start, end = rng[0], rng[1]
        # prune explicit y/q/m selections that conflict with a custom range
        sel_years, sel_quarters, sel_months = [], [], []

    return FilterSpec(
        start=start, end=end, custom_range=custom,
        years=sel_years, quarters=sel_quarters, months=sel_months,
        regions=sel_regions, territories=sel_territories, countries=sel_countries,
        categories=sel_categories, products=sel_products,
        segments=sel_segments, channels=sel_channels,
    )


def active_filter_chips(spec: FilterSpec) -> list[str]:
    """Human-readable active filters, e.g. '2026', 'North', 'Electronics'."""
    chips: list[str] = []
    if spec.custom_range and spec.start and spec.end:
        chips.append(f"{spec.start.strftime('%d %b %Y')} – {spec.end.strftime('%d %b %Y')}")
    else:
        chips.append(" · ".join(str(y) for y in spec.years) if spec.years else "All years")
        if spec.quarters:
            chips.append(" · ".join(spec.quarters))
        if spec.months:
            chips.append(" · ".join(spec.months))
    chips.append(" · ".join(spec.regions) if spec.regions else "All regions")
    if spec.territories:
        chips.append(" · ".join(spec.territories))
    if spec.countries:
        chips.append(" · ".join(spec.countries))
    chips.append(" · ".join(spec.categories) if spec.categories else "All categories")
    if spec.products:
        n = len(spec.products)
        chips.append(f"{n} products" if n > 3 else f"{n} product" + ("s" if n > 1 else ""))
    if spec.segments:
        chips.append(" · ".join(spec.segments))
    if spec.channels:
        chips.append(" · ".join(spec.channels))
    return chips
