"""Shared page-context builder.

app.py calls this after RBAC + user filters; the test harness reuses it so
context-building logic is never duplicated between production and tests.
"""

from __future__ import annotations

import pandas as pd

from src import filters, rls, metrics


def build_context(enriched: pd.DataFrame, role: str, spec: filters.FilterSpec) -> dict:
    """Apply RLS + user filters and assemble the page context (one place)."""
    rls_df = rls.apply_rls(enriched, role)
    df = filters.apply_filters(rls_df, spec)
    prev_spec = filters.previous_period_spec(spec, df)
    prev_df = (filters.apply_filters(rls_df, prev_spec)
               if prev_spec is not None else df.iloc[0:0])
    return {
        "df": df,
        "prev_df": prev_df,
        "full_df": rls_df,
        "spec": spec,
        "role": role,
        "net_revenue": metrics.net_revenue(df),
    }
