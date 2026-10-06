"""Data Quality page — computed checks, ETL repairs, model statistics and
the statistical Verification Engine that catches silent human error."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src import charts, data_quality, verifier
from src.formatting import format_datetime, format_int
from src.ui import kpi_card, kpi_row, page_header

_SEV_BADGE = {
    "high": '<span class="badge-danger">⚠ High</span>',
    "medium": '<span class="badge-warn">⚠ Medium</span>',
    "low": '<span class="badge-cert">· Low</span>',
}


def render(ctx: dict) -> None:
    page_header("Data Quality",
                "This dashboard is built on verified data — every check below is computed, not claimed.")
    result = data_quality.run_quality_checks()
    stats = result["stats"]

    # score + model stats
    left, right = st.columns([1, 3])
    with left:
        score = result["score"]
        fig = charts.donut_chart(
            pd.DataFrame({"Label": ["Pass", "Issues"], "Value": [score, 100 - score]}),
            "Label", "Value", center_title="Quality Score",
            center_value=f"{score:.1f}%", height=280,
            hover_texts=[f"{score:.2f}% of raw rows clean",
                         f"{100 - score:.2f}% of raw rows had issues (repaired)"])
        st.plotly_chart(fig, width="stretch", key="dq_score")
    with right:
        kpi_row([
            kpi_card("Records", format_int(stats["records"]),
                     sub=f"raw rows: {format_int(stats['raw_rows'])}"),
            kpi_card("Products", format_int(stats["products"])),
            kpi_card("Customers", format_int(stats["customers"])),
            kpi_card("Regions", format_int(stats["regions"]),
                     sub=f"{stats['date_start']} → {stats['date_end']}"),
        ])
        st.caption(f"Model generated: {format_datetime(stats['generated_at'])} "
                   f"(deterministic seed — every refresh reproduces the same numbers)")

    st.markdown("")
    left, right = st.columns(2)
    with left:
        st.markdown("**Integrity checks**")
        for check in result["checks"]:
            ok = check["status"] == "Pass"
            badge = '<span class="badge-cert">✓ Pass</span>' if ok else '<span class="badge-warn">⚠ Repaired</span>'
            st.markdown(
                '<div class="insight-item">'
                f'<div class="dq-row"><span class="dq-name">{check["name"]}</span>{badge}</div>'
                f'<div class="kpi-sub">{check["note"]} · {check["value"]} affected</div>'
                '</div>',
                unsafe_allow_html=True)
    with right:
        st.markdown("**ETL repair log (raw → governed model)**")
        repairs = stats.get("repairs", {})
        if repairs:
            for name, count in repairs.items():
                st.markdown(
                    '<div class="insight-item">'
                    f'<div class="dq-row"><span class="dq-name">{name.replace("_", " ").title()}</span>'
                    f'<span class="badge-warn">{count} repaired</span></div>'
                    '<div class="kpi-sub">Cleaned before entering the star schema</div>'
                    '</div>',
                    unsafe_allow_html=True)
        else:
            st.caption("No repairs required.")
        st.markdown("")
        st.markdown("**Model composition**")
        st.markdown(
            '<div class="insight-item">'
            '<div class="kpi-sub">Star schema: FACT_SALES + DIM_DATE + DIM_PRODUCT + '
            'DIM_CUSTOMER + DIM_TERRITORY in SQLite. Every fact joins cleanly to all four '
            'dimensions; revenue is verified against the governed formula row-by-row.</div>'
            '</div>',
            unsafe_allow_html=True)

    st.markdown("")
    st.markdown("**Verification Engine — statistical checks for silent human error**")
    st.caption("Rules catch typos and duplicates. Statistics catch the errors rules can't see: "
               "revenue swings, discount drift, return spikes and margin outliers. "
               "Every finding below is computed from the data — nothing is claimed.")
    # findings respect the role scope; model stats above are pipeline facts
    findings = verifier.scan(ctx["full_df"])
    if findings:
        for f in findings:
            st.markdown(
                f'<div class="insight-item alert-{"negative" if f["severity"] == "high" else "warning"}">'
                f'<div class="dq-row"><span class="dq-name">{f["title"]}</span>{_SEV_BADGE[f["severity"]]}</div>'
                f'<div class="insight-text">{f["finding"]}</div>'
                f'<div class="kpi-sub">Recommended: {f["action"]}</div>'
                '</div>',
                unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="insight-item alert-positive">'
            '<div class="dq-row"><span class="dq-name">✓ No statistical anomalies detected</span>'
            '<span class="badge-cert">✓ Clean</span></div>'
            '<div class="insight-text">Revenue movement, discounting, returns and margins are all '
            'within their normal statistical ranges for this scope.</div>'
            '</div>',
            unsafe_allow_html=True)
