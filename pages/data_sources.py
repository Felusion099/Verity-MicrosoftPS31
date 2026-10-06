"""Data Sources & Production Architecture page — shows the prototype vs production architecture."""

from __future__ import annotations

import streamlit as st

from src.ui import page_header


def render(ctx: dict) -> None:
    from src.ui import page_header

    page_header("Data Sources & Production Architecture",
                "Prototype vs. Production architecture — honest about what's implemented vs. planned.")

    st.markdown("## 🔧 Current Prototype")
    st.markdown("""
    The current Verity prototype demonstrates the complete PS31 solution with synthetic data:
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ✅ Implemented (Prototype)")
        st.markdown("""
        - **Governed Net Revenue**: Single certified definition (`Gross Sales − Discounts − Returns`)
        - **Star Schema**: FACT_SALES + 4 dimensions in SQLite
        - **82K transactions** with realistic patterns (seasonality, trends, anomalies)
        - **Governed Net Revenue** used everywhere (KPIs, charts, exports)
        - **11 global filters** with active chips + reset
        - **4 RLS roles** (Executive, Finance, North/South/East/West SM)
        - **AI Trainer**: Select invoices → learn norms → pinpoint mismatches
        - **Verification Engine**: Statistical anomaly detection (z-score, IQR, YoY)
        - **Forecasting**: Linear trend with 95% confidence band
        - **Metric Governance**: Certified definitions, live consistency proof
        - **Data Quality**: 9 integrity checks, ETL repair log, quality score
        - **AI Trainer**: Train on selected invoices → learn norms → pinpoint mismatches
        - **Export**: CSV + Markdown respecting filters + RLS
        - **Deterministic seed**: Reproducible data every run (seed 42)
        """)

    with col2:
        st.markdown("### 🔮 Production Architecture (Planned)")
        st.markdown("""
        | Layer | Prototype | Production |
        |-------|-----------|------------|
        **Data Sources** | Synthetic data (seed 42) | CRM (Salesforce), ERP (SAP/Oracle), Sales systems |
        **Ingestion** | Local CSV + SQLite | Airbyte/Fivetran → Kafka → Snowflake/BigQuery/Redshift |
| **Modeling** | SQLite star schema | dbt models on Snowflake/BigQuery |
| **Metrics** | Python functions (`metrics.py`) | dbt metrics / LookML / semantic layer |
| **Governance** | Python functions + Streamlit UI | dbt contracts + data contracts + Monte Carlo |
| **RLS** | Streamlit session state | Snowflake/BigQuery RLS + Entra ID |
| **AI/Anomaly** | Python (z-score, IQR) | Snowflake Cortex / Vertex AI / custom models |
| **Scheduling** | Manual "Local Refresh" | Airflow/Dagster + dbt Cloud + SLA alerts |
| **UI** | Streamlit | Power BI / Tableau / custom React |
| **Auth** | Demo role dropdown | Entra ID + SSO + RBAC |
| **Audit** | CSV export + Markdown | Immuta / Purview / Unity Catalog |
| **SLA** | None | 99.9% uptime, <5min latency, data contracts |

    """)

    st.markdown("---")
    st.markdown("### 📊 Data Flow Architecture")

    st.markdown("""
    ```
    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────┐
    │  CRM/ERP    │───▶│  Ingestion   │───▶│  Raw Zone   │───▶│  Staging    │───▶│  Core    │
    │  (Source)   │    │  (Airbyte/   │    │  (Bronze)   │    │  (Silver)   │    │  (Gold)  │
    │             │    │  Fivetran)   │    │  (Raw CSV)  │    │  (Cleaned)  │    │  (Star)  │
    └─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘    └──────────┘
                                                                                         │
                                                                                         ▼
                                                ┌─────────────┐    ┌──────────────┐    ┌──────────┐
                                                │  Governed   │───▶│  Anomaly    │───▶│  Verity  │
                                                │  Metrics    │    │  Engine     │    │  UI      │
                                                └─────────────┘    └──────────────┘    └──────────┘
    ```

    """)

    st.markdown("---")
    st.markdown("### 🎯 Key Differentiators")
    st.markdown("""
    1. **Governed Metrics First**: One definition of Net Revenue, certified and used everywhere
    2. **Finance ↔ Sales Reconciliation**: Single page showing target vs actual with drill-down
    3. **Anomaly Center**: DETECT → LOCALIZE → EXPLAIN → DRILL (not just charts)
    3. **AI Trainer**: Select invoices → learn norms → pinpoint mismatches
    4. **Verification Engine**: Statistical anomaly detection (z-score, IQR, YoY, drift)
    5. **Drill-through**: KPI → Region → Territory → Category → Product → Transaction
    4. **RLS Demo**: 6 roles showing territory-based security
    5. **Data Quality**: 9 integrity checks + ETL repair log + statistical verification
    6. **Honest Architecture**: Prototype vs Production clearly separated
    6. **Honest Refresh**: "Local Data Refresh" - no fake real-time claims
    """)

    st.markdown("---")
    st.caption("Verity · PS31 · Bennett Microsoft Innovate 2026 · One Definition. One Number. One Truth.")