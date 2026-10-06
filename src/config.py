"""Central configuration for Verity (Bennett Microsoft Innovate 2026 — PS31).

All business constants (targets, roles, metric ownership, dataset parameters,
paths) live here so business logic stays free of hardcoded values. Every path
is derived from __file__, so the app runs from any machine/directory.
"""

from pathlib import Path

# --------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATABASE_DIR = PROJECT_ROOT / "database"
DB_PATH = DATABASE_DIR / "analytics.db"
RAW_CSV_PATH = DATA_RAW_DIR / "sales_raw.csv"
BUILD_SUMMARY_PATH = DATA_PROCESSED_DIR / "build_summary.json"

# ------------------------------------------------------------- product shell
APP_NAME = "Verity"
APP_SUBTITLE = "Trusted Business Performance Intelligence"
APP_TAGLINE = "One Definition. One Number. One Truth."
PS_ID = "PS31"

# -------------------------------------------------------- dataset generation
DATA_SEED = 42
TARGET_ROW_COUNT = 75_000
DATE_START = "2024-01-01"
DATE_END = "2026-09-14"
ANNUAL_GROWTH = 0.16  # company-wide year-over-year demand growth baked into demand

# --------------------------------------------------------- governed metric
METRIC_OWNER = "Revenue Operations"
METRIC_SOURCE = "Enterprise Sales Model (SQLite star schema)"
# the formula itself is defined once in src/metrics.py (the metric authority)

# --------------------------------------------------- business targets (INR)
# Calibrated against the generated dataset so achievement bars are realistic.
# Monthly/quarterly targets are compared against the latest COMPLETE period;
# the annual target is compared against a trailing 12-month window.
MONTHLY_TARGET = 44_000_000
QUARTERLY_TARGET = 102_000_000
ANNUAL_TARGET = 445_000_000

# --------------------------------------------------- finance plan targets (INR)
# Finance Plan layer — calibrated so overall achievement ~88-92%,
# West underperforming (~80-85%), North outperforming (~95-100%).
# These are used as the Finance Plan targets for the Finance ↔ Sales page.
FINANCE_PLAN_MONTHLY_TARGET = 44_000_000
FINANCE_PLAN_QUARTERLY_TARGET = 102_000_000
FINANCE_PLAN_ANNUAL_TARGET = 445_000_000

# Regional distribution for Finance Plan targets (must sum to 1.0)
FINANCE_PLAN_REGION_WEIGHTS = {
    "North": 0.28,
    "South": 0.26,
    "West": 0.30,
    "East": 0.10,
    "Central": 0.06,
}

# Category weights for Finance Plan (must sum to 1.0)
FINANCE_PLAN_CATEGORY_WEIGHTS = {
    "Electronics": 0.28,
    "Home Appliances": 0.22,
    "Furniture": 0.15,
    "Office Supplies": 0.10,
    "Apparel": 0.08,
    "Sports & Fitness": 0.17,
}

# Monthly growth/decline factors for Finance Plan (seasonality)
FINANCE_PLAN_MONTHLY_FACTORS = {
    1: 0.92, 2: 0.90, 3: 1.12,  # Q4 FY / Q1 CY
    4: 0.95, 5: 0.98, 6: 0.90,  # Q1 FY
    7: 0.97, 8: 1.00, 9: 1.03,  # Q2 FY
    10: 1.15, 11: 1.22, 12: 1.08,  # Q3 FY (festive)
}

# ------------------------------------------------------------- demo RBAC
# Local simulation of territory-based row-level security. In production this
# would be driven by enterprise identity (Entra ID) — see README.
ROLES = {
    "Executive": {"regions": None, "label": "Full access — all regions"},
    "Finance": {"regions": None, "label": "Full access — all regions (global finance)"},
    "North Sales Manager": {"regions": ["North"], "label": "Restricted — North region only"},
    "South Sales Manager": {"regions": ["South"], "label": "Restricted — South region only"},
    "East Sales Manager": {"regions": ["East"], "label": "Restricted — East region only"},
    "West Sales Manager": {"regions": ["West"], "label": "Restricted — West region only"},
    "Finance Manager": {"regions": None, "label": "Full access — all regions (finance)"},
}
DEFAULT_ROLE = "Executive"

# ------------------------------------------------------------- UI palette
COLORS = {
    "primary": "#3b82f6",
    "cyan": "#22d3ee",
    "violet": "#a78bfa",
    "amber": "#fbbf24",
    "green": "#34d399",
    "red": "#f87171",
    "slate": "#64748b",
    "pink": "#f472b6",
}
PALETTE = [COLORS["primary"], COLORS["cyan"], COLORS["violet"], COLORS["amber"],
           COLORS["green"], COLORS["red"], COLORS["pink"], COLORS["slate"]]
