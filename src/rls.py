"""Demo Row-Level Security (RLS) by territory.

PS31 asks for row-level security by territory. This module SIMULATES the
architecture locally: a role maps to an allowed set of regions, and every
DataFrame handed to the dashboard passes through `apply_rls`. In production
the role would come from enterprise identity (e.g. Microsoft Entra ID) and
the same restriction would be enforced in the semantic layer / database —
never in the client. See README for the full explanation.
"""

from __future__ import annotations

import pandas as pd

from src import config


def allowed_regions(role: str) -> list[str] | None:
    """None means 'all regions permitted'; otherwise a list of region names."""
    return config.ROLES.get(role, {}).get("regions")


def is_restricted(role: str) -> bool:
    return allowed_regions(role) is not None


def apply_rls(df: pd.DataFrame, role: str) -> pd.DataFrame:
    """Restrict data to the regions permitted for this role.

    Called in app.py BEFORE user filters, so no filter combination can
    escape the role scope.
    """
    regions = allowed_regions(role)
    if regions is None or df.empty:
        return df
    return df[df["Region"].isin(regions)]
