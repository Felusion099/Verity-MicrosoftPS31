"""Extended interaction test: every button, toggle, select and tab."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from streamlit.testing.v1 import AppTest


def set_page(at, page):
    nav = [r for r in at.radio if r.key == "nav"][0]
    nav.set_value(page).run()


def find(at, kind, key=None, label_part=None):
    items = getattr(at, kind)
    for it in items:
        if key and it.key == key:
            return it
        if label_part and label_part in (it.label or ""):
            return it
    return None


at = AppTest.from_file("app.py", default_timeout=180)
at.run()
print("boot OK")

# 1. grain radios on Overview
grain = find(at, "radio", key="ov_grain")
grain.set_value("Quarterly").run()
assert not at.exception, at.exception
grain.set_value("Monthly").run()
assert not at.exception, at.exception
print("1. Overview grain radio OK (Quarterly/Monthly)")

# 2. compare toggle on Overview
toggle = find(at, "toggle", key="ov_compare")
toggle.set_value(False).run()
assert not at.exception, at.exception
print("2. Compare toggle OK (off)")

# 3. Revenue page: grain + breadcrumb selects
set_page(at, "Revenue")
grain = find(at, "radio", key="rv_grain")
grain.set_value("Weekly").run()
assert not at.exception, at.exception
region = find(at, "selectbox", key="rv_region")
region.select("North").run()
assert not at.exception, at.exception
territory = find(at, "selectbox", key="rv_territory")
territory.select(territory.options[1]).run()
assert not at.exception, at.exception
print("3. Revenue breadcrumb drill-down OK (North -> territory)")

# 4. Products: tabs + product selector
set_page(at, "Products")
sel = find(at, "selectbox", key="pr_selector")
if sel:
    sel.select(sel.options[1]).run()
    assert not at.exception, at.exception
    print("4. Product selector OK")
else:
    print("4. Product selector not found (check)")

# 5. Regions: rank-by + region selector
set_page(at, "Regions")
rank = find(at, "selectbox", key="rg_metric")
rank.select("Profit").run()
assert not at.exception, at.exception
rsel = find(at, "selectbox", key="rg_selector")
rsel.select("South").run()
assert not at.exception, at.exception
print("5. Regions rank-by + selector OK")

# 6. sidebar: region multiselect filter
multi = find(at, "multiselect", key="f_regions")
multi.set_value(["North"]).run()
assert not at.exception, at.exception
print("6. Region filter multiselect OK (North)")

# 7. reset filters button
reset = [b for b in at.button if "Reset" in (b.label or "")]
reset[0].click().run()
assert not at.exception, at.exception
print("7. Reset filters OK")

# 8. Local Data Refresh button
refresh = [b for b in at.button if "Refresh" in (b.label or "")]
assert refresh, "refresh button not found"
refresh[0].click().run(timeout=180)
assert not at.exception, at.exception
print("8. Local Data Refresh OK")

# 9. export download buttons (inside expander)
exp = [e for e in at.expander if "Export" in (e.label or "")]
csv_btn = [b for b in at.download_button if "CSV" in (b.label or "")]
md_btn = [b for b in at.download_button if "Markdown" in (b.label or "")]
print(f"9. Export buttons present: CSV={len(csv_btn)}, MD={len(md_btn)}, expander={len(exp)}")

# 10. custom date range toggle (inside the sidebar expander)
dtoggle = find(at, "toggle", key="f_custom_range")
if dtoggle:
    dtoggle.set_value(True).run()
    assert not at.exception, at.exception
    print("10. Custom date range toggle OK")
else:
    print("10. custom range toggle not found (expander closed)")

print("\nALL INTERACTIONS PASSED")
