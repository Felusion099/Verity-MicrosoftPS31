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

# ------------------------------------------------------------- demo RBAC
# Local simulation of territory-based row-level security. In production this
# would be driven by enterprise identity (Entra ID) — see README.
ROLES = {
    "Executive": {"regions": None, "label": "Full access — all regions"},
    "Finance": {"regions": None, "label": "Full access — all regions (global finance)"},
    "North Sales Manager": {"regions": ["North"], "label": "Restricted — North region only"},
    "South Sales Manager": {"regions": ["South"], "label": "Restricted — South region only"},
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
