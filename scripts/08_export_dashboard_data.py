"""
STEP 8b - Export the data for the Power BI dashboard
====================================================

What this script does, in plain words:
  Power BI works best with a few tidy tables. This script makes one main
  table, outputs/dashboard/portfolio_cube.csv, with one row for every
  combination of:
      approval year  x  industry  x  state  x  loan size
  and, for each row, the number of loans, dollars approved, number charged
  off and dollars lost.

  It is called a "cube" because you can slice it any way you like in Power BI
  (for example: only Ohio, only restaurants, only 2005-2008) and the totals
  still add up. It is much smaller than the 882,533-loan table, so it loads
  fast and is small enough to keep on GitHub.

  It also copies the tables from Steps 3-7 into the same folder, so all the
  dashboard's data is in one place.

How to run it:
    python scripts/08_export_dashboard_data.py
"""

from pathlib import Path
import shutil
import duckdb
import pandas as pd

PROJECT_FOLDER = Path(__file__).parent.parent
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"
OUTPUT_FOLDER = PROJECT_FOLDER / "outputs"
DASHBOARD_FOLDER = OUTPUT_FOLDER / "dashboard"
DASHBOARD_FOLDER.mkdir(parents=True, exist_ok=True)

# Tables made in earlier steps that the dashboard also uses
EARLIER_TABLES = [
    "vintage_performance.csv",     # Step 3
    "limit_monitor.csv",           # Step 4
    "vintage_curves.csv",          # Step 5
    "roll_forward.csv",            # Step 5
    "economic_indicators.csv",     # Step 6
    "early_warning_signals.csv",   # Step 6
    "lender_benchmark.csv",        # Step 7
    "state_benchmark.csv",         # Step 7
]

if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run Steps 1 and 2 first.")
    raise SystemExit

con = duckdb.connect(str(DATABASE_FILE), read_only=True)

# ---------------------------------------------------------------------------
# 1. Build the cube
# ---------------------------------------------------------------------------
cube = con.execute(
    """
    SELECT
        approval_year,
        CASE WHEN approval_year <= 2006 THEN 'Seasoned'
             WHEN approval_year <= 2010 THEN 'Partly seasoned'
             ELSE 'Too young to judge' END            AS seasoning,
        CASE
            WHEN approval_year <= 1999 THEN '1989-1999'
            WHEN approval_year <= 2004 THEN '2000-2004'
            WHEN approval_year <= 2008 THEN '2005-2008'
            WHEN approval_year <= 2010 THEN '2009-2010'
            ELSE '2011-2014'
        END                                           AS era,
        sector_name                                   AS industry,
        COALESCE(state, 'Not recorded')               AS state,
        loan_size_band,
        COUNT(*)                                      AS number_of_loans,
        SUM(loan_amount)                              AS approved_dollars,
        CAST(SUM(is_default) AS BIGINT)               AS loans_charged_off,
        SUM(charge_off_amount)                        AS dollars_charged_off
    FROM loans_clean
    GROUP BY ALL
    ORDER BY approval_year, industry, state, loan_size_band
    """
).df()

# ---------------------------------------------------------------------------
# 2. Check the cube adds up to the same totals as the full table
# ---------------------------------------------------------------------------
full = con.execute(
    """
    SELECT COUNT(*) AS loans, SUM(loan_amount) AS dollars,
           SUM(is_default) AS defaults, SUM(charge_off_amount) AS lost
    FROM loans_clean
    """
).fetchone()
con.close()

checks = [
    ("loans", full[0], cube["number_of_loans"].sum()),
    ("dollars approved", full[1], cube["approved_dollars"].sum()),
    ("loans charged off", full[2], cube["loans_charged_off"].sum()),
    ("dollars lost", full[3], cube["dollars_charged_off"].sum()),
]
print("Check: cube totals vs the full loans_clean table")
all_ok = True
for name, from_table, from_cube in checks:
    ok = abs(from_table - from_cube) < 1          # allow for tiny rounding
    all_ok = all_ok and ok
    print(f"   {name:<20} table {from_table:>20,.0f}   cube {from_cube:>20,.0f}   "
          f"{'OK' if ok else 'DIFFERENT'}")
if not all_ok:
    print("The totals don't match. Send this output to Claude before building the dashboard.")
    raise SystemExit

cube.to_csv(DASHBOARD_FOLDER / "portfolio_cube.csv", index=False)
print(f"\nSaved outputs/dashboard/portfolio_cube.csv ({len(cube):,} rows)")

# ---------------------------------------------------------------------------
# 3. Copy the earlier tables next to it
# ---------------------------------------------------------------------------
missing = []
for name in EARLIER_TABLES:
    source = OUTPUT_FOLDER / name
    if source.exists():
        shutil.copy(source, DASHBOARD_FOLDER / name)
    else:
        missing.append(name)

print(f"Copied {len(EARLIER_TABLES) - len(missing)} tables from earlier steps "
      "into outputs/dashboard/")

# Add a "dashboard_group" column to the lender table, so in Power BI you can
# show the 15 largest lenders plus KeyBank with a single filter.
lender_copy = DASHBOARD_FOLDER / "lender_benchmark.csv"
if lender_copy.exists():
    lenders = pd.read_csv(lender_copy)
    lenders["dashboard_group"] = "Other"
    lenders.loc[lenders["size_rank"] <= 15, "dashboard_group"] = "Top 15"
    lenders.loc[lenders["group_name"].str.upper().str.contains("KEYBANK"), "dashboard_group"] = "KeyBank"
    lenders.to_csv(lender_copy, index=False)
    print("Added a dashboard_group column to lender_benchmark.csv (Top 15 / KeyBank / Other)")
if missing:
    print("These were not found, so re-run the step that makes them:")
    for name in missing:
        print("   ", name)

print("\nDone! Next: build the dashboard in Power BI (see GUIDE_STEP8.md).")
