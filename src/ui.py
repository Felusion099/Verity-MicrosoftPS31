"""Shared UI components (HTML/CSS building blocks) used across pages.

Keeps page modules free of duplicated markup. Rendered with
st.markdown(..., unsafe_allow_html=True). Values passed in must already be
formatted via src.formatting.
"""

from __future__ import annotations

import streamlit as st


def page_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str | None = None,
             delta_class: str = "delta-flat", spark: str | None = None,
             sub: str | None = None) -> str:
    delta_html = f'<div class="kpi-delta {delta_class}">{delta}</div>' if delta else ""
    spark_html = f'<div class="kpi-spark">{spark}</div>' if spark else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return (
        '<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta_html}{spark_html}{sub_html}'
        '</div>'
    )


def kpi_row(cards: list[str]) -> None:
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        col.markdown(card, unsafe_allow_html=True)


def empty_state(title: str, hint: str) -> None:
    st.markdown(
        '<div class="empty-state">'
        f'<div class="empty-title">{title}</div>'
        f'<div class="empty-hint">{hint}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def insight_item(level: str, title: str, text: str) -> None:
    """level: 'positive' | 'neutral' | 'negative' | 'warning'."""
    st.markdown(
        f'<div class="insight-item alert-{level}">'
        f'<div class="insight-title">{title}</div>'
        f'<div class="insight-text">{text}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def target_row(label: str, pct: float, actual: str, target: str) -> str:
    width = max(0.0, min(100.0, pct))
    color = "var(--green)" if pct >= 100 else ("var(--amber)" if pct >= 85 else "var(--red)")
    return (
        '<div class="target-row">'
        f'<div class="target-head"><span>{label}</span><span>{pct:.1f}%</span></div>'
        f'<div class="target-bar"><div class="target-fill" style="width:{width:.1f}%; background:{color};"></div></div>'
        f'<div class="target-sub">Actual {actual} &nbsp;·&nbsp; Target {target}</div>'
        '</div>'
    )


def status_badge(text: str = "✓ Certified") -> str:
    return f'<span class="badge-cert">{text}</span>'


def chip(text: str, muted: bool = False) -> str:
    cls = "chip chip-muted" if muted else "chip"
    return f'<span class="{cls}">{text}</span>'
