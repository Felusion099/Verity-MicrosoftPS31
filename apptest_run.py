"""Full AppTest run: render every page (via the test harness), exercise RBAC,
key interactive controls, and catch exceptions."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from streamlit.testing.v1 import AppTest

HARNESS = "tests/render_harness.py"
PAGES = ["overview", "revenue", "products", "regions", "customers",
         "data_quality", "ai_trainer", "governance"]


def fresh(page: str | None = None, role: str | None = None, timeout: int = 180) -> AppTest:
    at = AppTest.from_file(HARNESS, default_timeout=timeout)
    if page:
        at.query_params["page"] = page
    if role:
        at.query_params["role"] = role
    at.run()
    return at


def find(at, kind, key):
    for it in getattr(at, kind):
        if it.key == key:
            return it
    return None


# ---- 1. every page renders without exceptions (Executive) ----------------
for page in PAGES:
    at = fresh(page)
    assert not at.exception, f"Exception on page {page}: {at.exception}"
print("1. all 8 pages render OK (Executive)")

# ---- 2. key pages with RESTRICTED role -----------------------------------
for page in ("overview", "revenue", "regions", "ai_trainer"):
    at = fresh(page, role="North Sales Manager")
    assert not at.exception, f"Exception restricted {page}: {at.exception}"
print("2. restricted pages OK (North Sales Manager)")

# ---- 3. main app shell boots, RBAC widget works ---------------------------
at = AppTest.from_file("app.py", default_timeout=180)
at.run()
assert not at.exception, f"Exception on main app: {at.exception}"
find(at, "selectbox", "role").set_value("North Sales Manager").run()
assert not at.exception, "Exception with North role on main app"
print("3. main app shell + RBAC role switch OK")

# ---- 4. interactive controls ----------------------------------------------
at = fresh("overview")
find(at, "radio", "ov_grain").set_value("Quarterly").run()
assert not at.exception, "Exception on grain radio"
print("4. Overview grain radio OK")

at = fresh("revenue")
find(at, "slider", "rv_whatif").set_value(15.0).run()
assert not at.exception, "Exception on what-if slider"
print("5. Revenue what-if slider OK")

at = fresh("ai_trainer")
find(at, "slider", "at_tol").set_value(3.0).run()
assert not at.exception, "Exception on strictness slider"
print("6. AI Trainer strictness slider OK")

print("\nAPPTEST PASSED")
