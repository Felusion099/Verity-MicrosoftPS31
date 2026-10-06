"""AI Trainer page — build a training set by SELECTING invoices, learn the
norms of that exact scope, then pinpoint the statements that mismatch.
Interactive front-end for src/trainer.py."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from src import metrics, trainer
from src.formatting import format_inr, format_int, format_pct
from src.ui import empty_state, kpi_card, kpi_row, page_header

_ORDER_KEYS = ["OrderID", "Date", "Region", "Territory", "Segment"]


def _order_view(df: pd.DataFrame) -> pd.DataFrame:
    """One row per order with context columns + governed measures."""
    return metrics.aggregate_by(df, _ORDER_KEYS).sort_values("Date", ascending=False)


def _training_set_builder(df: pd.DataFrame) -> list[str]:
    """Selectable invoice table -> training set (persisted in session state)."""
    ss = st.session_state
    orders = _order_view(df)
    view = orders[["OrderID", "Date", "Region", "Territory", "Segment",
                   "Lines", "NetRevenue"]].copy()
    view["Date"] = pd.to_datetime(view["Date"]).dt.date
    st.markdown("**Build a training set — select invoices below, then add them**")
    event = st.dataframe(
        view, on_select="rerun", selection_mode="multi-row",
        width="stretch", height=300, hide_index=True, key="at_inv_table",
        column_config={
            "OrderID": st.column_config.TextColumn("Order ID", width="small"),
            "Date": st.column_config.DateColumn("Date", width="small"),
            "Region": st.column_config.TextColumn("Region", width="small"),
            "Territory": st.column_config.TextColumn("Territory", width="small"),
            "Segment": st.column_config.TextColumn("Segment", width="small"),
            "Lines": st.column_config.NumberColumn("Items", width="small"),
            "NetRevenue": st.column_config.NumberColumn("Net Revenue", format="₹,.0f"),
        },
    )
    selected = event.selection.rows if hasattr(event, "selection") else []
    selected_ids = view.iloc[selected]["OrderID"].tolist() if selected else []

    c1, c2, c3 = st.columns([1.4, 1, 4])
    if c1.button("＋ Add selection to training set", width="stretch"):
        current = ss.get("at_training_set") or []
        merged = list(dict.fromkeys(current + selected_ids))  # keep order, unique
        ss.at_training_set = merged
        st.rerun()
    if c2.button("✕ Clear training set", width="stretch"):
        ss.at_training_set = []
        st.rerun()

    training_set = ss.get("at_training_set") or []
    if training_set:
        st.caption(f"Training set: {len(training_set)} invoice(s) — "
                   f"{', '.join(training_set[:6])}" + (", …" if len(training_set) > 6 else ""))
    else:
        st.caption("No invoices selected — the trainer trains on the whole current scope.")
    return training_set


def _learned_section(profile: dict) -> None:
    """What the trainer learned from the training scope."""
    left, right = st.columns(2)
    with left:
        st.markdown("**Learned: discount norms by segment**")
        seg = pd.DataFrame(profile["segment_discount_norm"]).T.reset_index()
        seg.columns = ["Segment", "Mean discount %", "Std %"]
        st.dataframe(seg, width="stretch", height=180, hide_index=True, key="at_seg")
    with right:
        st.markdown("**Learned: return norms by category**")
        cat = pd.DataFrame({"Category": list(profile["category_return_norm"]),
                            "Return rate %": list(profile["category_return_norm"].values())})
        st.dataframe(cat, width="stretch", height=180, hide_index=True, key="at_cat")


def _findings_section(findings: list[dict], totals: dict, summary: dict, tol: float) -> None:
    """Pinpointed statements with expected vs actual and causes."""
    st.markdown("")
    if not findings:
        st.markdown(
            '<div class="insight-item alert-positive">'
            '<div class="dq-row"><span class="dq-name">✓ All statements match</span>'
            '<span class="badge-cert">✓ Clean</span></div>'
            '<div class="insight-text">Every statement obeys the governed formulas and sits within '
            'the learned norms for this training scope and strictness.</div></div>',
            unsafe_allow_html=True)
        return

    st.markdown("**Pinpointed statements**")
    sev_filter = st.multiselect("Severity", ["high", "medium"], default=["high", "medium"],
                                key="at_sev")
    view = [f for f in findings if f["severity"] in sev_filter] or findings
    rows = pd.DataFrame(view)
    st.dataframe(
        rows[["order_id", "date", "product", "region", "segment", "rule_label",
              "column", "expected", "actual", "cause"]],
        width="stretch", height=420, hide_index=True, key="at_findings",
        column_config={
            "order_id": st.column_config.TextColumn("Order ID", width="small"),
            "date": st.column_config.TextColumn("Date", width="small"),
            "product": st.column_config.TextColumn("Product", width="medium"),
            "region": st.column_config.TextColumn("Region", width="small"),
            "segment": st.column_config.TextColumn("Segment", width="small"),
            "rule_label": st.column_config.TextColumn("Rule broken", width="medium"),
            "column": st.column_config.TextColumn("Column", width="small"),
            "expected": st.column_config.TextColumn("Expected", width="small"),
            "actual": st.column_config.TextColumn("Actual", width="small"),
            "cause": st.column_config.TextColumn("Likely cause", width="large"),
        },
    )
    st.caption(f"Showing {len(view):,} of {summary['total']:,} pinpointed statements · "
               f"high = exact formula violations · medium = outside learned norms "
               f"(strictness {tol:.1f}σ).")


def _invoice_inspector(df: pd.DataFrame, training_set: list[str]) -> None:
    """Pick one invoice -> full line-item detail with per-row verification."""
    st.markdown("")
    st.markdown("**Inspect a specific invoice**")
    if training_set:
        options = sorted(training_set)
    else:
        options = _order_view(df)["OrderID"].unique().tolist()[:500]
        st.caption("Showing the 500 most recent orders — add invoices to the training set to inspect others.")
    if not options:
        empty_state("No orders in the current scope", "Widen the filters.")
        return
    inv = st.selectbox("Order ID", options, key="at_inv_select")
    inv_rows = df[df["OrderID"] == inv]
    if len(inv_rows) == 0:
        empty_state("Order not found in the current scope", "Widen the filters or clear the training set.")
        return

    detail = inv_rows[["Date", "Region", "Territory", "ProductName", "Quantity",
                       "UnitPrice", "GrossSales", "DiscountAmount", "ReturnAmount",
                       "NetRevenue", "Profit"]].copy()
    detail["Expected Net"] = (detail["GrossSales"] - detail["DiscountAmount"]
                              - detail["ReturnAmount"])  # governed formula
    detail["Status"] = np.where((detail["NetRevenue"] - detail["Expected Net"]).abs() > 0.01,
                                "⚠ Mismatch", "✓ OK")
    detail["Date"] = pd.to_datetime(detail["Date"]).dt.date
    kpi_row([
        kpi_card("Invoice", inv, sub=f"{int(detail['Quantity'].sum())} units"),
        kpi_card("Invoice Net Revenue", format_inr(detail["Expected Net"].sum()),
                 sub=f"{format_int(len(detail))} line items"),
        kpi_card("Line items verified", format_int(int((detail["Status"] == "✓ OK").sum())),
                 sub=f"{int((detail['Status'] != '✓ OK').sum())} mismatching"),
    ])
    st.dataframe(
        detail, width="stretch", height=260, hide_index=True, key="at_inv_detail",
        column_config={
            "Date": st.column_config.DateColumn("Date", width="small"),
            "Region": st.column_config.TextColumn("Region", width="small"),
            "Territory": st.column_config.TextColumn("Territory", width="small"),
            "ProductName": st.column_config.TextColumn("Product", width="medium"),
            "Quantity": st.column_config.NumberColumn("Qty", width="small"),
            "UnitPrice": st.column_config.NumberColumn("Unit Price", format="₹,.0f"),
            "GrossSales": st.column_config.NumberColumn("Gross", format="₹,.0f"),
            "DiscountAmount": st.column_config.NumberColumn("Discount", format="₹,.0f"),
            "ReturnAmount": st.column_config.NumberColumn("Returns", format="₹,.0f"),
            "NetRevenue": st.column_config.NumberColumn("Net Revenue", format="₹,.0f"),
            "Expected Net": st.column_config.NumberColumn("Expected Net (governed)", format="₹,.0f"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )


def render(ctx: dict) -> None:
    df = ctx["df"]
    page_header("AI Trainer",
                "Select invoices to train on — the trainer learns that scope's norms, "
                "pinpoints mismatching statements, and explains the cause.")

    if df is None or len(df) == 0:
        empty_state("No data in the current scope to train on",
                    "Widen the filters or reset them — the trainer trains on whatever scope you choose.")
        return

    training_set = _training_set_builder(df)

    # training scope: the selected invoices, or the whole current scope
    scope_rows = df[df["OrderID"].isin(training_set)] if training_set else df

    tol = st.slider("Strictness (σ) — lower catches more, higher only flags extremes",
                    min_value=1.0, max_value=3.0, value=2.0, step=0.5, key="at_tol")

    if len(scope_rows) == 0:
        empty_state("Selected invoices are outside the current filter scope",
                    "Clear the training set or widen the filters.")
        return

    # Phase 1: LEARN on the exact training scope
    profile = trainer.build_profile(scope_rows)
    findings, totals = trainer.pinpoint(scope_rows, profile, tolerance=tol)
    summary = trainer.summarize(findings, totals)

    hard = sum(v for k, v in totals.items()
               if k in ("revenue_formula", "profit_formula", "gross_formula",
                        "over_refund", "discount_overflow", "negative_values"))
    learned = totals.get("discount_outlier", 0) + totals.get("lead_time_anomaly", 0)
    st.markdown("")
    kpi_row([
        kpi_card("Statements scanned", f"{profile['rows_scanned']:,}",
                 sub="trained on this exact scope"),
        kpi_card("Formula violations", f"{hard:,}",
                 sub="exact statements breaking governed formulas" if hard else "governed model intact ✓"),
        kpi_card("Norm outliers", f"{learned:,}",
                 sub=f"beyond {tol:.1f}σ of the learned norms"),
        kpi_card("Findings shown", f"{len(findings):,}",
                 sub="exact rows with expected vs actual"),
    ])

    _learned_section(profile)
    _findings_section(findings, totals, summary, tol)
    _invoice_inspector(df, training_set)
