"""Reusable Plotly chart functions with a consistent enterprise dark theme.

All charts share one template so the dashboard looks like one product.
Revenue axes are plotted in ₹ Cr for readability; hover tooltips show the
governed, fully formatted value via precomputed customdata.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

from src import config
from src.formatting import format_inr

PRIMARY = config.COLORS["primary"]
GRID = "rgba(148,163,184,0.10)"
LINE = "rgba(148,163,184,0.22)"

# register the shared enterprise template once
_TEMPLATE = go.layout.Template()
_TEMPLATE.layout = go.Layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, 'Segoe UI', system-ui, sans-serif", size=12.5, color="#cbd5e1"),
    hoverlabel=dict(bgcolor="#1e293b", bordercolor="#334155", font=dict(color="#e2e8f0", size=12.5)),
    xaxis=dict(gridcolor=GRID, zerolinecolor=LINE, linecolor=LINE, showline=True),
    yaxis=dict(gridcolor=GRID, zerolinecolor=LINE, linecolor=LINE, showline=True),
    legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0),
    margin=dict(l=8, r=8, t=40, b=8),
)
pio.templates["verity"] = _TEMPLATE
pio.templates.default = "verity"


def _layout(fig: go.Figure, height: int, title: str | None = None, legend: bool = False) -> go.Figure:
    fig.update_layout(height=height, title=title,
                      showlegend=legend, hovermode="x unified")
    fig.update_xaxes(tickfont=dict(size=11))
    fig.update_yaxes(tickfont=dict(size=11))
    return fig


def empty_fig(message: str, height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False,
                       font=dict(size=13, color="#8fa3bf"), xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_layout(height=height)
    return fig


def _y_vals(df: pd.DataFrame, y) -> np.ndarray:
    """Accept a column name or a precomputed list/array of values."""
    return df[y].to_numpy() if isinstance(y, str) else np.asarray(y, dtype=float)


def revenue_area_chart(df: pd.DataFrame, x: str, y, hover_texts: list[str],
                       name: str, color: str = PRIMARY,
                       compare_df: pd.DataFrame | None = None,
                       compare_x=None, compare_y=None,
                       compare_name: str = "Previous period",
                       y_title: str | None = None, height: int = 340) -> go.Figure:
    """Interactive line/area trend with an optional dashed previous-period line.

    `y` holds the plotted values (column name or list, e.g. Net Revenue in ₹ Cr);
    `hover_texts` holds fully formatted values for the tooltip.
    """
    if df is None or len(df) == 0:
        return empty_fig("No data in this period", height)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x], y=_y_vals(df, y), name=name, fill="tozeroy",
        line=dict(color=color, width=2.4, shape="spline"),
        fillcolor="rgba(59,130,246,0.10)",
        customdata=hover_texts,
        hovertemplate="%{customdata}<extra></extra>",
    ))
    if compare_df is not None and len(compare_df) > 0 and compare_y is not None:
        cx = compare_df[compare_x] if isinstance(compare_x, str) else compare_x
        cy = compare_df[compare_y] if isinstance(compare_y, str) else _y_vals(compare_df, compare_y)
        fig.add_trace(go.Scatter(
            x=cx, y=cy,
            name=compare_name, line=dict(color="#64748b", width=1.6, dash="dot", shape="spline"),
        ))
    fig.update_layout(yaxis_title=y_title)
    return _layout(fig, height, legend=compare_df is not None)


def column_chart(df: pd.DataFrame, x: str, y, hover_texts: list[str],
                 title: str | None = None, color: str | list[str] = PRIMARY,
                 height: int = 320) -> go.Figure:
    """Vertical bars (regions, channels, months...)."""
    if df is None or len(df) == 0:
        return empty_fig("No data", height)
    fig = go.Figure(go.Bar(
        x=df[x], y=_y_vals(df, y), marker_color=color, marker_line_width=0,
        customdata=hover_texts,
        hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.update_layout(title=title)
    return _layout(fig, height)


def hbar_chart(df: pd.DataFrame, x: str, y, hover_texts: list[str],
               title: str | None = None, color: str = PRIMARY, height: int = 380) -> go.Figure:
    """Horizontal bars, best-ranked on top (top products, territories...).

    `x` = label column, `y` = numeric column or list, `hover_texts` = formatted
    values aligned with `df` order (reordered together when sorting).
    """
    if df is None or len(df) == 0:
        return empty_fig("No data", height)
    labels = df[x].to_numpy()
    values = _y_vals(df, y)
    hovers = np.asarray(hover_texts, dtype=object)
    order = np.argsort(values)  # horizontal bars draw bottom-up → best on top
    fig = go.Figure(go.Bar(
        x=values[order], y=labels[order], orientation="h",
        marker_color=color, marker_line_width=0,
        customdata=hovers[order],
        hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.update_layout(title=title)
    return _layout(fig, height)


def donut_chart(df: pd.DataFrame, names: str, values: str,
                center_title: str = "", center_value: str = "",
                height: int = 320, hover_texts: list[str] | None = None) -> go.Figure:
    """Revenue mix donut with a KPI in the hole. Optional formatted hover texts."""
    if df is None or len(df) == 0:
        return empty_fig("No data", height)
    hover = hover_texts if hover_texts else [f"{v:,.0f}" for v in df[values]]
    fig = go.Figure(go.Pie(
        labels=df[names], values=df[values], hole=0.62,
        marker_colors=config.PALETTE, marker_line=dict(color="#0b1220", width=2),
        textinfo="percent", textfont=dict(size=11, color="#cbd5e1"),
        customdata=hover,
        hovertemplate="%{label}<br>%{customdata}<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{center_value}</b><br><span style='font-size:11px'>{center_title}</span>",
                       showarrow=False, font=dict(size=16, color="#e2e8f0"), x=0.5, y=0.5)
    return _layout(fig, height, legend=True)


def scatter_quadrant(df: pd.DataFrame, x: str, y: str, text_col: str,
                     x_title: str, y_title: str, height: int = 380) -> go.Figure:
    """Profitability quadrants: X = Net Revenue (₹ Cr), Y = Profit Margin (%)."""
    if df is None or len(df) == 0:
        return empty_fig("No data", height)
    d = df.copy()
    fig = px.scatter(d, x=d[x] / 1e7, y=d[y], text=text_col,
                     color_discrete_sequence=[PRIMARY], opacity=0.75)
    fig.update_traces(textposition="top center", textfont=dict(size=8.5, color="#94a3b8"),
                      marker=dict(size=9, line=dict(width=0)),
                      hovertemplate="%{text}<br>Net Revenue: " + "%{customdata}" + "<br>Margin: %{y:.1f}%<extra></extra>",
                      customdata=[format_inr(v) for v in d[x]])
    xm, ym = d[x].mean() / 1e7, d[y].mean()
    fig.add_hline(y=ym, line=dict(color="#475569", width=1, dash="dash"))
    fig.add_vline(x=xm, line=dict(color="#475569", width=1, dash="dash"))
    fig.update_layout(xaxis_title=x_title, yaxis_title=y_title)
    return _layout(fig, height)


def sparkline_svg(values: list[float], color: str = PRIMARY,
                  width: int = 132, height: int = 36) -> str:
    """Tiny inline SVG polyline for KPI cards (no chart engine needed)."""
    vals = [v for v in values if pd.notna(v)]
    if len(vals) < 2 or max(vals) == min(vals) == 0:
        return ""
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        x = 2 + i / (len(vals) - 1) * (width - 4)
        y = height - 4 - (v - lo) / span * (height - 8)
        pts.append(f"{x:.1f},{y:.1f}")
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<polyline fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" points="{" ".join(pts)}"/></svg>')


def forecast_chart(hist_df: pd.DataFrame, fc_df: pd.DataFrame, height: int = 320) -> go.Figure:
    """Governed history (solid) + linear forecast (dashed) + confidence band."""
    if hist_df is None or len(hist_df) == 0:
        return empty_fig("Not enough history to forecast", height)
    x_hist = hist_df["Label"].tolist()
    y_hist = [v / 1e7 for v in hist_df["NetRevenue"]]
    # bridge the forecast from the last history point
    x_fc = [x_hist[-1]] + fc_df["Label"].tolist()
    y_fc = [y_hist[-1]] + [v / 1e7 for v in fc_df["Forecast"]]
    y_hi = [y_hist[-1]] + [v / 1e7 for v in fc_df["Hi"]]
    y_lo = [y_hist[-1]] + [v / 1e7 for v in fc_df["Lo"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_hist, y=y_hist, name="Net Revenue", fill="tozeroy",
        line=dict(color=PRIMARY, width=2.4, shape="spline"),
        fillcolor="rgba(59,130,246,0.10)",
        customdata=[format_inr(v) for v in hist_df["NetRevenue"]],
        hovertemplate="%{customdata}<extra></extra>",
    ))
    # 95% confidence band
    fig.add_trace(go.Scatter(x=x_fc, y=y_hi, mode="lines", line=dict(width=0),
                             hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=x_fc, y=y_lo, mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(251,191,36,0.15)",
                             hoverinfo="skip", showlegend=False, name="95% band"))
    fig.add_trace(go.Scatter(
        x=x_fc, y=y_fc, name="Forecast (linear trend)",
        line=dict(color=config.COLORS["amber"], width=2, dash="dot", shape="spline"),
        customdata=[format_inr(float(hist_df["NetRevenue"].iloc[-1]))]
                   + [format_inr(v) for v in fc_df["Forecast"]],
        hovertemplate="Forecast: %{customdata}<extra></extra>",
    ))
    fig.update_layout(yaxis_title="Net Revenue (₹ Cr)")
    return _layout(fig, height, legend=True)


TERRITORY_COORDS = {
    "Delhi NCR": (28.61, 77.21), "Chandigarh": (30.73, 76.78), "Jaipur": (26.91, 75.79), "Lucknow": (26.85, 80.95),
    "Bengaluru": (12.97, 77.59), "Chennai": (13.08, 80.27), "Hyderabad": (17.38, 78.49), "Kochi": (9.93, 76.27),
    "Mumbai": (19.08, 72.88), "Pune": (18.52, 73.86), "Ahmedabad": (23.03, 72.58), "Nagpur": (21.15, 79.09),
    "Kolkata": (22.57, 88.36), "Bhubaneswar": (20.30, 85.82), "Patna": (25.59, 85.14), "Guwahati": (26.14, 91.74),
    "Bhopal": (23.26, 77.41), "Indore": (22.72, 75.86), "Raipur": (21.25, 81.63), "Jabalpur": (23.18, 79.99),
}


def map_bubble_chart(df: pd.DataFrame, height: int = 420) -> go.Figure:
    """India bubble map: bubble size = Net Revenue, colour = region.

    Uses Plotly's built-in geo layers (client-side, no external geo files) —
    reliable by design, matching the PS31 guidance on maps.
    """
    d = df[df["Territory"].isin(TERRITORY_COORDS)].copy()
    if d is None or len(d) == 0:
        return empty_fig("No mapped territories in scope", height)
    d["lat"] = d["Territory"].map(lambda t: TERRITORY_COORDS[t][0])
    d["lon"] = d["Territory"].map(lambda t: TERRITORY_COORDS[t][1])
    max_cr = max(float((d["NetRevenue"] / 1e7).max()), 1e-9)
    d["size"] = 12 + 26 * ((d["NetRevenue"] / 1e7) / max_cr)
    regions = sorted(d["Region"].unique())
    region_colors = {r: config.PALETTE[i % len(config.PALETTE)] for i, r in enumerate(regions)}
    hover = [f"{t} · {format_inr(v)} · {r}" for t, v, r in zip(d["Territory"], d["NetRevenue"], d["Region"])]
    fig = go.Figure(go.Scattergeo(
        lat=d["lat"], lon=d["lon"], mode="markers",
        marker=dict(size=d["size"], color=d["Region"].map(region_colors), opacity=0.85,
                    line=dict(color="#0b1220", width=1)),
        customdata=hover,
        hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.update_geos(
        scope="asia", fitbounds="locations", showcountries=True, countrycolor="#334155",
        showland=True, landcolor="#141d31", showocean=True, oceancolor="rgba(0,0,0,0)",
        showcoastlines=True, coastlinecolor="#334155", showframe=False, showlakes=False,
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(title="Territory map — bubble size = Net Revenue",
                      margin=dict(l=0, r=0, t=40, b=0))
    return fig
