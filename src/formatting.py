"""Central formatting module — the ONLY place numbers/dates get formatted.

Indian currency notation (₹ Cr / ₹ L) and Indian digit grouping are used
throughout so every screen, chart and export reads consistently.
"""

from __future__ import annotations

import pandas as pd


def format_int(value: float) -> str:
    """Indian digit grouping: 1284540 -> '12,84,540'."""
    if value is None or pd.isna(value):
        return "—"
    n = int(round(float(value)))
    sign = "-" if n < 0 else ""
    s = str(abs(n))
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return sign + ",".join(groups) + "," + tail


def format_inr(value: float, decimals: int = 1) -> str:
    """Indian-notation currency: ₹48.2 Cr / ₹7.4 L / ₹84,200."""
    if value is None or pd.isna(value):
        return "—"
    sign = "-" if value < 0 else ""
    mag = abs(float(value))
    if mag >= 1e7:
        body = f"{mag / 1e7:.{decimals}f} Cr"
    elif mag >= 1e5:
        body = f"{mag / 1e5:.{decimals}f} L"
    else:
        return sign + "₹" + format_int(mag)
    return f"{sign}₹{body}"


def format_pct(value: float, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{decimals}f}%"


def format_num(value: float, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    if decimals == 0:
        return format_int(value)
    return f"{value:,.{decimals}f}"


def format_date(value) -> str:
    """'14 Sep 2026' style dates."""
    if value is None or pd.isna(value):
        return "—"
    ts = pd.Timestamp(value)
    return ts.strftime("%d %b %Y")


def format_datetime(value) -> str:
    """'14 Sep 2026, 12:30 PM' style timestamps."""
    if value is None:
        return "—"
    ts = pd.Timestamp(value)
    return ts.strftime("%d %b %Y, %I:%M %p")


def delta_text(current: float, previous: float) -> tuple[str, str]:
    """Compare current vs previous value -> (display text, css class).

    Previous period growth: (current - previous) / |previous| * 100.
    """
    if previous is None or pd.isna(previous) or abs(previous) < 1e-9:
        return "—", "delta-flat"
    change = (float(current) - float(previous)) / abs(float(previous)) * 100.0
    arrow = "▲" if change >= 0 else "▼"
    cls = "delta-up" if change >= 0 else "delta-down"
    return f"{arrow} {abs(change):.1f}%", cls
