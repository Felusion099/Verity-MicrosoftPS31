"""Dependency-free forecast: linear trend projection on the governed monthly series.

Honest by design: a simple linear projection of the governed Net Revenue
series with a 95% confidence band. The UI labels it as a linear trend —
production forecasting would use seasonal models.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import metrics


def forecast_monthly(df: pd.DataFrame, periods_ahead: int = 3,
                     min_months: int = 6) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Project monthly Net Revenue forward.

    Returns (history_df, forecast_df) or None when the series is too short.
    history_df: Label, NetRevenue. forecast_df: Label, Forecast, Lo, Hi.
    """
    trend = metrics.revenue_trend(df, "Monthly")
    if len(trend) < min_months:
        return None
    x = np.arange(len(trend), dtype=float)
    y = trend["NetRevenue"].to_numpy(dtype=float)
    coef = np.polyfit(x, y, 1)
    sigma = float(np.std(y - np.polyval(coef, x)))
    band = 1.96 * sigma  # ~95% confidence interval

    last_period = trend["Period"].iloc[-1]
    labels, preds, lo, hi = [], [], [], []
    for i in range(1, periods_ahead + 1):
        pred = max(0.0, float(np.polyval(coef, len(trend) - 1 + i)))
        labels.append((last_period + i).strftime("%b %Y"))
        preds.append(pred)
        lo.append(max(0.0, pred - band))
        hi.append(pred + band)

    hist = trend[["Label", "NetRevenue"]].copy()
    fc = pd.DataFrame({"Label": labels, "Forecast": preds, "Lo": lo, "Hi": hi})
    return hist, fc
