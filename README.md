# Verity

**Trusted Business Performance Intelligence**
*One Definition. One Number. One Truth.*

Bennett University Microsoft Innovate 2026 Hackathon — Problem Statement 31: **"The Number the Whole Company Trusts."**

---

## Problem Statement (PS31)

Sales and Finance disagree on what "revenue" means. Different teams use different calculations, spreadsheets, filters and definitions, so every management meeting starts with arguments about the numbers. PS31 asks for a **single source of truth for business performance** — including a governed metric, drill-through analysis, territory-level security and trusted data quality.

## Business Problem

- Teams calculate revenue with different formulas and spreadsheets
- Every dashboard, deck and meeting shows a different number
- Manual reconciliation wastes time and erodes trust in reporting

## Solution

**Verity** — an internal enterprise analytics platform for Revenue Operations / Finance / Sales that runs fully locally:

- **One governed metric:** exactly one definition of NET REVENUE (`Gross Sales − Discounts − Returns`) used by every KPI, chart, table and export
- **A real analytical model:** star schema (`FACT_SALES` + 4 dimensions) in SQLite — not one flat CSV
- **Executive dashboard:** revenue, growth, orders, units, AOV, top products, regional performance, trends — all calculated from data, never hardcoded
- **Governance you can see:** Metric Governance page with the certified definition, metric catalog and a live consistency proof
- **Territory security (demonstrated):** demo row-level security by region
- **Honest architecture:** local data refresh, no fake real-time, no paid APIs, no cloud, no API keys

---

## Key Features

| Area | What it does |
|---|---|
| Overview | 6 KPI cards (sparklines + vs-previous-period deltas), revenue trend (Daily/Weekly/Monthly/Quarterly + comparison), **linear trend forecast with 95% band**, region bars, category mix, top products, profitability quadrants, targets, executive insights, attention flags |
| Revenue | Breadcrumb drill-down (Region → Territory → Category → Product), transaction table with search/sort, CSV export, channel mix, **what-if discount simulator** |
| Products | Top/bottom/fastest-growing/highest-margin/most-discounted/highest-return rankings + full product detail |
| Regions | Ranked region bars by any metric, growth by region, contribution donut, region detail with territory breakdown, leaders & laggards, **India bubble map** |
| Customers | Segment KPIs, revenue/orders/AOV by segment, top 15 customers |
| Data Quality | Computed quality score, integrity checks (✓/⚠), ETL repair log, model statistics |
| **Verification Engine** | Statistical anomaly detection for silent human error: revenue swings, order-volume anomalies, YoY regressions, discount drift, return spikes, margin outliers — each with a plain-language explanation and recommended action (`src/verifier.py`) |
| **AI Trainer** | Standalone verification trainer (`src/trainer.py`, also a dashboard page): **build a training set by selecting invoices** (native row-selection), the trainer LEARNS that scope's norms (per-segment discount norms, per-category return norms), PINPOINTS the exact statements that mismatch — formula violations with expected vs actual per row — and EXPLAINS the likely cause. Adjustable strictness (σ); invoice inspector with per-line verification. CLI: `python -m src.trainer` |
| Metric Governance | Certified NET REVENUE hero card, formula flow, metric catalog, live consistency proof |

Plus: 11 global filters + reset + active-filter chips, demo RBAC (Executive / Finance / North SM / South SM), configurable targets with achievement bars, executive insights & alerts (only when the underlying condition is true), CSV + Markdown export respecting filters and role scope, honest "Local Data Refresh".

---

## Architecture

```
PS31/
├── app.py                  # Shell: header, sidebar nav, RBAC, filters, refresh, export
├── requirements.txt
├── README.md
├── data/
│   ├── raw/                # sales_raw.csv — raw landing zone (with injected data-entry issues)
│   └── processed/          # build_summary.json — records, repairs, totals
├── database/
│   └── analytics.db        # SQLite star schema
├── src/
│   ├── config.py           # Targets, roles, paths, palette (no hardcoded business logic)
│   ├── data_generator.py   # Synthetic dataset + ETL (repairs dirty data, records repairs)
│   ├── data_loader.py      # Cached loads: SQLite → enriched fact view
│   ├── metrics.py          # GOVERNED METRIC LAYER — single source of truth
│   ├── filters.py          # Declarative filter spec applied identically everywhere
│   ├── charts.py           # Reusable Plotly charts, enterprise dark theme
│   ├── insights.py         # Auto insights + alerts (computed, never hallucinated)
│   ├── data_quality.py     # Computed checks + quality score
│   ├── verifier.py         # Statistical verification engine (anomaly detection)
│   ├── trainer.py          # AI Trainer — learns norms, pinpoints mismatching statements (standalone CLI)
│   ├── forecast.py         # Dependency-free linear trend forecast + confidence band
│   ├── rls.py              # Demo row-level security by territory
│   ├── formatting.py       # ₹ Cr / ₹ L / Indian grouping — the only place numbers are formatted
│   └── ui.py               # Shared KPI cards, badges, chips, empty states
├── pages/                  # overview, revenue, products, regions, customers,
│                           # data_quality, ai_trainer, governance
└── assets/                 # logo
```

## Data Model (Star Schema)

| Table | Grain | Key columns |
|---|---|---|
| `FACT_SALES` | 1 row = order line item | SalesKey, OrderID, DateKey, ProductKey, CustomerKey, TerritoryKey, SalesChannel, Quantity, UnitPrice, GrossSales, DiscountAmount, ReturnAmount, NetRevenue, Cost, Profit |
| `DIM_DATE` | 1 row = day | DateKey, Date, Day, Week, Month, MonthName, Quarter, Year, FiscalYear (Apr–Mar), FiscalQuarter |
| `DIM_PRODUCT` | 1 row = product | ProductKey, ProductID, ProductName, Category, Subcategory |
| `DIM_CUSTOMER` | 1 row = customer | CustomerKey, CustomerID, CustomerName, Segment |
| `DIM_TERRITORY` | 1 row = territory | TerritoryKey, Region, Territory, Country |

## Metric Definitions (Governed)

**NET REVENUE = Gross Sales − Discounts − Returns** — Owner: Revenue Operations — Status: ✓ Certified

The exact formula is defined **once** in `src/metrics.py` (`net_revenue()`). Every revenue figure in the application flows through it. The Data Quality page verifies every stored `NetRevenue` value against this formula row-by-row, and the Metric Governance page proves live consistency: governed metric = stored column = sum of chart aggregates.

| Metric | Definition | Owner |
|---|---|---|
| Net Revenue | Gross Sales − Discounts − Returns | Revenue Operations |
| Gross Revenue | SUM(Gross Sales) | Finance |
| Profit | Net Revenue − Cost | Finance |
| Profit Margin | Profit ÷ Net Revenue | Finance |
| Orders | COUNT(DISTINCT Order ID) | Sales Operations |
| Average Order Value | Net Revenue ÷ Orders | Revenue Operations |
| Units Sold | SUM(Quantity) | Supply Chain Operations |
| Return Rate | Returned line items ÷ total line items | Sales Operations |

## Technology Stack

- **Python 3** (tested on 3.14) — application + ETL
- **Streamlit** — custom enterprise dark dashboard shell
- **pandas + NumPy** — transformation, aggregations, insights
- **Plotly** — interactive, themed visualizations
- **SQLite** — star-schema analytical store (plus a raw CSV landing zone)
- No paid APIs, no cloud services, no API keys, no Power BI dependency

## The Dataset

~75,000→80,000 synthetic transaction rows (deterministic **seed = 42**), 1 Jan 2024 → 14 Sep 2026, generated in `src/data_generator.py`:

- ~130 products across 6 categories, ~3,500 customers in 4 segments, 5 regions / 20 territories (India)
- Realistic patterns: festive Oct–Dec demand peak, FY-end March push, summer dip, weekend B2B slowdown, region/territory performance differences, rising & declining product life-cycles, segment-based discounting, ~3–5% returns, month-to-month noise
- The raw CSV layer intentionally contains **data-entry issues** (duplicate rows, region typos, missing dates). The ETL repairs them and reports every repair — surfaced on the Data Quality page
- Stored in `data/raw/sales_raw.csv` + `database/analytics.db`; auto-generated on first run if missing

## How to Install

```bash
cd ~/Documents/microsoft/hackathon/PS31
python3 -m venv venv            # or use an existing environment
source venv/bin/activate
pip install -r requirements.txt
```

## How to Run

```bash
python -m src.data_generator    # optional: pre-build the dataset
python -m streamlit run app.py  # → http://localhost:8501
```

The app auto-generates the dataset on first launch if the database is missing.

## Demo Instructions

1. Open the dashboard — KPIs, growth and the ✓ Certified badge land in the first 30 seconds
2. Point at **Certified Net Revenue — Gross Sales − Discounts − Returns**
3. Change the Region filter — every KPI, chart and chip updates together
4. Open **Regions** → drill into a territory → show leaders and laggards
5. Open **Products** → select a product → trend, margin, return rate
6. Open **Revenue** → drill down to transaction rows → export CSV
7. Open **Metric Governance** → formula, catalog, live consistency proof
8. Switch role to **North Sales Manager** — the whole dashboard restricts to North
9. Open **Data Quality** — computed checks, ETL repairs, quality score
10. Close: *"One company. One definition. One number."*

## RLS Explanation

PS31 requires row-level security by territory. Because this is a local hackathon application, the architecture is **simulated, not faked**: a demo role selector (in `src/rls.py` + `config.ROLES`) maps each role to an allowed set of regions, and **every** DataFrame passes through `apply_rls` *before* user filters — no filter combination can escape the role scope. Exports respect it too.

In production, the role would come from enterprise identity (e.g. Microsoft Entra ID) and the same restriction would be enforced in the semantic layer / database — never in the client. The local dropdown is a demonstration of territory-based access control architecture, **not** production authentication.

## Data-Quality Checks (all computed)

- Missing order dates / product IDs / customer IDs
- Duplicate order line items (de-duplicated on SalesKey in ETL)
- Invalid region labels (standardized in ETL)
- NetRevenue matches the governed formula (row-by-row verification)
- Negative revenue records; return amount exceeding net of discount
- Orphan facts (no dimension match)
- Quality score = 100 × (1 − raw issues ÷ raw rows)

Plus the **Verification Engine** (`src/verifier.py`): statistical anomaly detection that catches the silent human errors rules can't — month-to-month revenue swings beyond ±2σ, YoY revenue regressions, discount drift, return-rate spikes and product margin outliers. Every finding is computed, explained in plain language, and paired with a recommended verification action.

## How This Solves PS31

| PS31 requirement | Implementation |
|---|---|
| Governed Net Revenue (single definition) | `src/metrics.py` — one central function + Metric Governance page with certified catalog |
| Star schema / analytical model | `FACT_SALES` + 4 dimensions in SQLite, joined via `src/data_loader.py` |
| Revenue, growth, orders, units, AOV, top products, regions, trends | Overview page — all computed via governed metrics |
| Date / product / regional filtering | `src/filters.py` — 11 declarative filters + reset + active chips |
| Drill-down / drill-through analysis | Breadcrumb drill-down + product/region detail views + searchable transaction table |
| Row-level security by territory | `src/rls.py` demo RBAC (would connect to Entra ID in production) |
| Scheduled refresh | Local refresh architecture (cache clear + reload) with honest labeling |
| Data quality | `src/data_quality.py` — computed checks, ETL repair log, quality score |
| Export | CSV + Markdown exports respecting filters and role scope |

## Limitations

- Local demo: no concurrent multi-user access, no live data ingestion; refresh is an honest local reload
- RBAC is simulated locally — not production authentication
- Synthetic data (deterministic), though engineered to be realistic
- Indian currency formatting is used in KPIs/insights; data tables use standard digit grouping

## Future Improvements

- Microsoft Entra ID SSO + enforced RLS in the semantic layer
- Scheduled ingestion from source systems (incremental loads)
- Forecasting (Prophet / statsmodels) on the revenue trend
- Write-back commentary and approvals on governed metrics
- PDF / PowerPoint export of executive summaries
