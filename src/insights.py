"""Executive insights + attention alerts, generated FROM the data.

Every sentence here is backed by an actual calculation — nothing is
hardcoded, nothing is hallucinated. If a condition isn't true in the data,
the insight or alert simply isn't shown.
"""

from __future__ import annotations

import pandas as pd

from src import metrics
from src.formatting import format_inr, format_pct


def generate_insights(df: pd.DataFrame) -> list[dict]:
    """Computed executive insights for the currently filtered scope."""
    insights: list[dict] = []
    if df is None or len(df) == 0:
        return insights
    total = metrics.net_revenue(df)

    # 1) top region + contribution share
    by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
    if len(by_region):
        top = by_region.iloc[0]
        share = top["NetRevenue"] / total * 100 if total > 0 else 0
        insights.append({
            "level": "positive",
            "title": f"{top['Region']} leads all regions",
            "text": f"{top['Region']} is the highest-revenue region, contributing "
                    f"{share:.1f}% of total Net Revenue ({format_inr(top['NetRevenue'])}).",
        })

    # 2) category momentum: last complete quarter vs the one before it
    end = df["Date"].max()
    q = end.to_period("Q")
    q_start, q_end = q.start_time.normalize(), q.end_time.normalize()
    if q_start > df["Date"].min():  # only if the quarter has started
        cur_q = df[(df["Date"] >= q_start) & (df["Date"] <= q_end)]
        prev_q = df[(df["Date"] < q_start) & (df["Date"] >= q_start - pd.DateOffset(months=3))]
        if len(cur_q) and len(prev_q):
            cat_q = metrics.aggregate_by(cur_q.assign(P="c"), ["P", "Category"])
            cat_p = metrics.aggregate_by(prev_q.assign(P="p"), ["P", "Category"])
            m = cat_q.merge(cat_p, on="Category", suffixes=("_c", "_p"))
            m["Growth"] = (m["NetRevenue_c"] - m["NetRevenue_p"]) / m["NetRevenue_p"] * 100
            m = m[m["NetRevenue_p"] > 0].sort_values("NetRevenue_c", ascending=False)
            if len(m):
                best = m.iloc[0]
                trend = "grew" if best["Growth"] >= 0 else "declined"
                insights.append({
                    "level": "positive" if best["Growth"] >= 0 else "warning",
                    "title": f"{best['Category']} tops the current quarter",
                    "text": f"{best['Category']} generated {format_inr(best['NetRevenue_c'])} this quarter "
                            f"and {trend} {abs(best['Growth']):.1f}% versus the previous quarter.",
                })

    # 3) high revenue but below-average margin product
    by_prod = metrics.aggregate_by(df, ["ProductName"])
    if len(by_prod) >= 5:
        avg_margin = by_prod["Margin"].mean()
        rev_p75 = by_prod["NetRevenue"].quantile(0.75)
        weak = by_prod[(by_prod["NetRevenue"] >= rev_p75) & (by_prod["Margin"] < avg_margin - 5)]
        if len(weak):
            w = weak.sort_values("NetRevenue", ascending=False).iloc[0]
            insights.append({
                "level": "warning",
                "title": f"{w['ProductName']}: high revenue, weak margin",
                "text": f"{w['ProductName']} is a top-revenue product but its profit margin "
                        f"({w['Margin']:.1f}%) is below the portfolio average ({avg_margin:.1f}%).",
            })

    # 4) discounting impact on margin
    deep = df[df["DiscountRate"] > 0.15]
    light = df[df["DiscountRate"] <= 0.15]
    if len(deep) >= 50 and len(light) >= 50:
        m_deep = metrics.profit_margin(deep)
        m_light = metrics.profit_margin(light)
        if m_deep < m_light:
            insights.append({
                "level": "neutral",
                "title": "Deep discounting erodes margin",
                "text": f"Transactions discounted above 15% average a {m_deep:.1f}% margin versus "
                        f"{m_light:.1f}% at lower discounts — discounting above 15% is associated with lower profit margins.",
            })

    # 5) latest month-over-month movement
    trend = metrics.revenue_trend(df, "Monthly")
    if len(trend) >= 2:
        last, prev = trend.iloc[-1], trend.iloc[-2]
        change = (last["NetRevenue"] - prev["NetRevenue"]) / prev["NetRevenue"] * 100 if prev["NetRevenue"] else 0
        insights.append({
            "level": "positive" if change >= 0 else "negative",
            "title": f"{last['Label']} MoM: {change:+.1f}%",
            "text": f"Net Revenue in {last['Label']} was {format_inr(last['NetRevenue'])}, "
                    f"{change:+.1f}% versus {prev['Label']} ({format_inr(prev['NetRevenue'])}).",
        })

    # 6) fastest-growing product (last 90 days vs prior 90)
    growth = metrics.window_growth_by(df, ["ProductName"], days=90, min_lines=10)
    if len(growth):
        fastest = growth.sort_values("Growth", ascending=False).iloc[0]
        if pd.notna(fastest["Growth"]) and fastest["Growth"] > 5:
            insights.append({
                "level": "positive",
                "title": f"{fastest['ProductName']} is accelerating",
                "text": f"{fastest['ProductName']} grew {fastest['Growth']:.1f}% in the last 90 days "
                        f"({format_inr(fastest['NetRevenue'])} vs {format_inr(fastest['PrevNetRevenue'])} in the prior window).",
            })

    return insights


def generate_alerts(df: pd.DataFrame) -> list[dict]:
    """'Attention Required' flags — only shown when the condition is actually true."""
    alerts: list[dict] = []
    if df is None or len(df) == 0:
        return alerts

    # 1) regions that declined >10% last complete quarter
    end = df["Date"].max()
    q = end.to_period("Q")
    q_start = q.start_time.normalize()
    cur_q = df[df["Date"] >= q_start]
    prev_q = df[(df["Date"] < q_start) & (df["Date"] >= q_start - pd.DateOffset(months=3))]
    if len(cur_q) and len(prev_q):
        rq = metrics.aggregate_by(cur_q, ["Region"])[["Region", "NetRevenue", "Orders"]]
        rp = metrics.aggregate_by(prev_q, ["Region"])[["Region", "NetRevenue"]].rename(
            columns={"NetRevenue": "PrevNet"})
        m = rq.merge(rp, on="Region")
        m["Growth"] = (m["NetRevenue"] - m["PrevNet"]) / m["PrevNet"] * 100
        for _, row in m[m["Growth"] < -10].sort_values("Growth").iterrows():
            alerts.append({
                "level": "negative",
                "title": f"⚠ {row['Region']} revenue declined {abs(row['Growth']):.1f}%",
                "text": f"{row['Region']} fell from {format_inr(row['PrevNet'])} to {format_inr(row['NetRevenue'])} "
                        f"this quarter — more than the 10% alert threshold.",
            })

    # 2) products with return rate well above company average
    company_rr = metrics.return_rate(df)
    by_prod = metrics.aggregate_by(df, ["ProductName"])
    risky = by_prod[(by_prod["Lines"] >= 30) & (by_prod["ReturnRate"] > company_rr * 1.5)]
    if len(risky):
        top = risky.sort_values("ReturnRate", ascending=False).iloc[0]
        alerts.append({
            "level": "warning",
            "title": f"⚠ {top['ProductName']} return rate {top['ReturnRate']:.1f}%",
            "text": f"Return rate is above the company average of {company_rr:.1f}% "
                    f"({int(top['Returns'])} returned line items).",
        })

    # 3) products growing while margin shrinks
    if len(cur_q) and len(prev_q):
        cq = metrics.aggregate_by(cur_q, ["ProductName"])
        pq = metrics.aggregate_by(prev_q, ["ProductName"])[["ProductName", "NetRevenue"]].rename(
            columns={"NetRevenue": "PrevNet"})
        mm = cq.merge(pq, on="ProductName")
        mm["Growth"] = (mm["NetRevenue"] - mm["PrevNet"]) / mm["PrevNet"] * 100
        bad = mm[(mm["PrevNet"] > 0) & (mm["Growth"] > 15) & (mm["Margin"] < metrics.profit_margin(cur_q) - 5)
                 & (mm["Lines"] >= 20)]
        if len(bad):
            b = bad.sort_values("NetRevenue", ascending=False).iloc[0]
            alerts.append({
                "level": "warning",
                "title": f"⚠ {b['ProductName']}: revenue up, margin down",
                "text": f"Revenue grew {b['Growth']:.1f}% this quarter while margin sits at "
                        f"{b['Margin']:.1f}% — pricing review recommended.",
            })

    # 4) positive flag: best region outpacing company growth this quarter
    if len(cur_q) and len(prev_q):
        comp_growth = (metrics.net_revenue(cur_q) - metrics.net_revenue(prev_q)) / metrics.net_revenue(prev_q) * 100 \
            if metrics.net_revenue(prev_q) else 0
        rqs = metrics.aggregate_by(cur_q, ["Region"])
        rps = metrics.aggregate_by(prev_q, ["Region"])[["Region", "NetRevenue"]].rename(
            columns={"NetRevenue": "PrevNet"})
        rr = rqs.merge(rps, on="Region")
        rr["Growth"] = (rr["NetRevenue"] - rr["PrevNet"]) / rr["PrevNet"] * 100
        leader = rr.sort_values("Growth", ascending=False).iloc[0]
        if comp_growth > 0 and leader["Growth"] > comp_growth:
            alerts.append({
                "level": "positive",
                "title": f"✓ {leader['Region']} is outpacing company growth",
                "text": f"{leader['Region']} grew {leader['Growth']:.1f}% this quarter versus "
                        f"{comp_growth:.1f}% company-wide — exceeding the quarterly trajectory.",
            })

    return alerts


def executive_summary_md(df: pd.DataFrame, prev_df: pd.DataFrame | None) -> str:
    """Executive summary export (Markdown) for the currently filtered scope."""
    k = metrics.kpi_summary(df)
    lines = [
        "# Verity — Executive Summary",
        "",
        "_Generated from the governed Net Revenue definition (Gross Sales − Discounts − Returns)._",
        "",
        "## Key metrics",
        "",
        f"- **Net Revenue:** {format_inr(k['net_revenue'])}",
        f"- **Gross Revenue:** {format_inr(k['gross_revenue'])}",
        f"- **Orders:** {k['orders']:,}",
        f"- **Units Sold:** {k['units_sold']:,}",
        f"- **Gross Profit:** {format_inr(k['profit'])} ({format_pct(k['profit_margin'])} margin)",
        f"- **Average Order Value:** {format_inr(k['aov'])}",
        f"- **Return Rate:** {format_pct(k['return_rate'])}",
    ]
    if prev_df is not None and len(prev_df):
        pk = metrics.kpi_summary(prev_df)
        if pk["net_revenue"]:
            growth = (k["net_revenue"] - pk["net_revenue"]) / pk["net_revenue"] * 100
            lines.append(f"- **Growth vs previous period:** {growth:+.1f}%")
    lines += ["", "## Top regions by Net Revenue", ""]
    by_region = metrics.aggregate_by(df, ["Region"]).sort_values("NetRevenue", ascending=False)
    total = k["net_revenue"] or 1
    for _, row in by_region.iterrows():
        lines.append(f"- {row['Region']}: {format_inr(row['NetRevenue'])} ({row['NetRevenue'] / total * 100:.1f}%)")
    lines += ["", "## Top products by Net Revenue", ""]
    by_prod = metrics.aggregate_by(df, ["ProductName"]).sort_values("NetRevenue", ascending=False).head(10)
    for _, row in by_prod.iterrows():
        lines.append(f"- {row['ProductName']}: {format_inr(row['NetRevenue'])}")
    lines += ["", "## Executive insights", ""]
    for ins in generate_insights(df):
        lines.append(f"- **{ins['title']}** — {ins['text']}")
    lines += ["", "## Attention required", ""]
    alerts = generate_alerts(df)
    if alerts:
        for a in alerts:
            lines.append(f"- **{a['title']}** — {a['text']}")
    else:
        lines.append("- No flags raised in the current scope.")
    lines += ["", "---", "", "_Verity · One Definition. One Number. One Truth._"]
    return "\n".join(lines)
