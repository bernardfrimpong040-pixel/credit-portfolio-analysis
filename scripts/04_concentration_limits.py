"""
STEP 4b - Concentration limits and charts
=========================================

What this script does, in plain words:
  1. Works out each industry's and each state's share of the money lent
     (loans approved 2001-2010, the same loans as sql/04_concentrations.sql)
  2. Gives each group a LIMIT: the most of the portfolio it is allowed to hold.
     Riskier groups get a smaller limit (a "risk-adjusted" limit).
  3. Compares each share with its limit and gives a status:
       Breach -> the share is ABOVE the limit
       Watch  -> the share has used 80% or more of the limit
       Within -> comfortably inside the limit
  4. Saves the results to  outputs/limit_monitor.csv
  5. Draws two charts in  outputs/ :
       industry_concentration.png : share of dollars vs share of losses
       loan_size_risk.png         : default rate by loan size

IMPORTANT: the limit numbers below are EXAMPLE settings chosen for this project,
not SBA or bank policy. Real banks set them in their risk appetite and review
them every year (the job posting calls this "annual recalibration of portfolio
tolerances and limits"). Change them at the top and re-run to see the effect.

How to run it:
    python scripts/04_concentration_limits.py
"""

from pathlib import Path
import duckdb
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_FOLDER = Path(__file__).parent.parent
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"
OUTPUT_FOLDER = PROJECT_FOLDER / "outputs"
OUTPUT_FOLDER.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# The limit settings (example values - change them and re-run)
# ---------------------------------------------------------------------------
FIRST_YEAR, LAST_YEAR = 2001, 2010

INDUSTRY_LIMIT_PCT = 15.0          # normal limit: at most 15% of dollars in one industry
INDUSTRY_LIMIT_HIGH_RISK_PCT = 10.0  # tighter limit for high-risk industries
STATE_LIMIT_PCT = 10.0             # normal limit: at most 10% of dollars in one state
STATE_LIMIT_HIGH_RISK_PCT = 7.5    # tighter limit for high-risk states

HIGH_RISK_INDEX = 1.25   # a risk index above this counts as "high risk"
WATCH_LEVEL = 0.80       # "Watch" once a group has used 80% of its limit

# Chart colours (same look as Step 3)
BLUE = "#2a78d6"      # share of dollars
ORANGE = "#eb6834"    # share of losses
TEXT = "#0b0b0b"
TEXT_SOFT = "#52514e"
GRID = "#e4e3df"
BACKGROUND = "#fcfcfb"

if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run Steps 1 and 2 first.")
    raise SystemExit

con = duckdb.connect(str(DATABASE_FILE), read_only=True)


# ---------------------------------------------------------------------------
# 1. A helper that builds the share-and-risk table for any column
# ---------------------------------------------------------------------------
def shares_and_risk(column):
    """Return one row per group with its share of dollars, share of losses
    and risk index. 'column' is the SQL for the grouping, e.g. 'sector_name'."""
    return con.execute(
        f"""
        SELECT
            {column}                                                     AS group_name,
            COUNT(*)                                                     AS number_of_loans,
            100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER ()     AS pct_of_dollars,
            100.0 * SUM(charge_off_amount)
                  / SUM(SUM(charge_off_amount)) OVER ()                  AS pct_of_losses,
            100.0 * AVG(is_default)                                      AS default_rate_pct
        FROM loans_clean
        WHERE approval_year BETWEEN {FIRST_YEAR} AND {LAST_YEAR}
        GROUP BY {column}
        """
    ).df()


industries = shares_and_risk("sector_name")
states = shares_and_risk("COALESCE(state, 'Not recorded')")

for table in (industries, states):
    table["risk_index"] = table["pct_of_losses"] / table["pct_of_dollars"]


# ---------------------------------------------------------------------------
# 2. Give every group its limit and status
# ---------------------------------------------------------------------------
def apply_limits(table, dimension, normal_limit, high_risk_limit):
    table = table.copy()
    table.insert(0, "dimension", dimension)

    # Riskier groups get the tighter limit
    table["limit_pct"] = [
        high_risk_limit if risk > HIGH_RISK_INDEX else normal_limit
        for risk in table["risk_index"]
    ]
    # How much room is left before the limit (negative = already over)
    table["headroom_pct"] = table["limit_pct"] - table["pct_of_dollars"]
    # How much of the limit is used, e.g. 0.9 = 90% used
    table["limit_used"] = table["pct_of_dollars"] / table["limit_pct"]

    statuses = []
    for used in table["limit_used"]:
        if used > 1:
            statuses.append("Breach")
        elif used >= WATCH_LEVEL:
            statuses.append("Watch")
        else:
            statuses.append("Within")
    table["status"] = statuses
    return table


monitor = pd.concat(
    [
        apply_limits(industries, "Industry", INDUSTRY_LIMIT_PCT, INDUSTRY_LIMIT_HIGH_RISK_PCT),
        apply_limits(states, "State", STATE_LIMIT_PCT, STATE_LIMIT_HIGH_RISK_PCT),
    ],
    ignore_index=True,
)

# Round for a tidy file, and sort so the biggest problems come first
monitor = monitor.round({"pct_of_dollars": 2, "pct_of_losses": 2, "default_rate_pct": 1,
                         "risk_index": 2, "limit_pct": 1, "headroom_pct": 2,
                         "limit_used": 2})
status_order = {"Breach": 0, "Watch": 1, "Within": 2}
monitor = monitor.sort_values(
    by=["status", "limit_used"],
    key=lambda col: col.map(status_order) if col.name == "status" else -col,
)
monitor.to_csv(OUTPUT_FOLDER / "limit_monitor.csv", index=False)
print("Saved outputs/limit_monitor.csv\n")

# Print the groups that need attention
needs_attention = monitor[monitor["status"] != "Within"]
print(f"Groups at or near their limit ({len(needs_attention)} of {len(monitor)}):")
if needs_attention.empty:
    print("   none - every industry and state is comfortably within its limit")
else:
    columns_to_show = ["dimension", "group_name", "pct_of_dollars", "risk_index",
                       "limit_pct", "headroom_pct", "status"]
    print(needs_attention[columns_to_show].to_string(index=False))


# ---------------------------------------------------------------------------
# 3. Chart helpers (same clean look as Step 3)
# ---------------------------------------------------------------------------
def tidy_axes(ax, grid_axis):
    ax.set_facecolor(BACKGROUND)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left", "bottom"]:
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=TEXT_SOFT, labelsize=9, length=0)


# ---------------------------------------------------------------------------
# 4. Chart 1: each industry's share of dollars vs its share of losses
#    Two bars per industry. When the orange bar is longer than the blue one,
#    that industry loses more than its size would suggest.
# ---------------------------------------------------------------------------
chart_data = industries.sort_values("pct_of_dollars")      # biggest ends up at the top
positions = range(len(chart_data))
bar_height = 0.38

figure, ax = plt.subplots(figsize=(10, 0.42 * len(chart_data) + 1.6))
figure.patch.set_facecolor(BACKGROUND)
ax.barh([p + bar_height / 2 for p in positions], chart_data["pct_of_dollars"],
        height=bar_height, color=BLUE, label="Share of dollars lent",
        edgecolor=BACKGROUND, linewidth=1)
ax.barh([p - bar_height / 2 for p in positions], chart_data["pct_of_losses"],
        height=bar_height, color=ORANGE, label="Share of dollars lost",
        edgecolor=BACKGROUND, linewidth=1)
ax.set_yticks(list(positions))
ax.set_yticklabels(chart_data["group_name"], color=TEXT, fontsize=9)
tidy_axes(ax, "x")
ax.set_xlabel("% of portfolio", color=TEXT_SOFT, fontsize=9)
ax.legend(loc="lower right", frameon=True, facecolor=BACKGROUND,
          edgecolor=BACKGROUND, fontsize=9, labelcolor=TEXT_SOFT)
figure.suptitle("Industry concentration: share of money lent vs share of money lost",
                x=0.01, ha="left", fontsize=12, color=TEXT, fontweight="bold")
ax.set_title(f"Loans approved {FIRST_YEAR}-{LAST_YEAR}. Orange longer than blue = "
             "the industry lost more than its size would suggest.",
             loc="left", fontsize=9, color=TEXT_SOFT)
figure.tight_layout()
figure.savefig(OUTPUT_FOLDER / "industry_concentration.png", dpi=150)
plt.close(figure)
print("\nSaved outputs/industry_concentration.png")

# ---------------------------------------------------------------------------
# 5. Chart 2: default rate by loan size
# ---------------------------------------------------------------------------
sizes = con.execute(
    f"""
    SELECT
        loan_size_band,
        100.0 * AVG(is_default) AS default_rate_pct
    FROM loans_clean
    WHERE approval_year BETWEEN {FIRST_YEAR} AND {LAST_YEAR}
    GROUP BY loan_size_band
    ORDER BY loan_size_band
    """
).df()
con.close()

# Remove the "1. " numbering we used for sorting, for nicer labels
sizes["label"] = sizes["loan_size_band"].str.split(". ", n=1).str[1]
# matplotlib treats text between two $ signs as a maths formula, so we put a
# backslash before each $ to tell it "this is just a dollar sign"
sizes["label"] = sizes["label"].str.replace("$", r"\$", regex=False)

figure, ax = plt.subplots(figsize=(8, 4.2))
figure.patch.set_facecolor(BACKGROUND)
ax.bar(sizes["label"], sizes["default_rate_pct"], width=0.6, color=BLUE,
       edgecolor=BACKGROUND, linewidth=1.5)
for x, y in zip(sizes["label"], sizes["default_rate_pct"]):
    ax.annotate(f"{y:.1f}%", xy=(x, y), xytext=(0, 4), textcoords="offset points",
                ha="center", fontsize=9, color=TEXT)     # only 5 bars, so label each
tidy_axes(ax, "y")
ax.spines["bottom"].set_visible(True)
ax.spines["bottom"].set_color(TEXT_SOFT)
ax.set_ylabel("% of loans charged off", color=TEXT_SOFT, fontsize=9)
ax.set_xlabel("Loan size", color=TEXT_SOFT, fontsize=9)
ax.set_title(f"Default rate by loan size (loans approved {FIRST_YEAR}-{LAST_YEAR})",
             loc="left", fontsize=12, color=TEXT, fontweight="bold")
figure.tight_layout()
figure.savefig(OUTPUT_FOLDER / "loan_size_risk.png", dpi=150)
plt.close(figure)
print("Saved outputs/loan_size_risk.png")

print("\nDone! Open outputs/limit_monitor.csv in Excel to see every group.")
