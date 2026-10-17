"""
STEP 5b - Vintage curve and roll-forward charts
===============================================

What this script does, in plain words:
  1. Builds the vintage curves: for each approval year (2001-2013), the % of
     loans charged off by each loan age (1 year old, 2 years old, ...)
  2. Builds the yearly roll-forward and its annual charge-off rate (2001-2014)
  3. Saves both as CSV files in  outputs/
  4. Draws two charts in  outputs/ :
       vintage_curves.png        : every vintage as a grey line, with a
                                   calm year (2002) and a crisis year (2007)
                                   highlighted so you can compare them
       annual_chargeoff_rate.png : % of outstanding loans charged off each year

How to run it:
    python scripts/05_roll_forward_charts.py
"""

from pathlib import Path
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_FOLDER = Path(__file__).parent.parent
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"
OUTPUT_FOLDER = PROJECT_FOLDER / "outputs"
OUTPUT_FOLDER.mkdir(exist_ok=True)

DATA_YEAR = 2014          # the year the data was collected
CALM_VINTAGE = 2002       # a vintage from before the boom
CRISIS_VINTAGE = 2007     # the worst vintage from Step 3

# Chart colours (same look as Steps 3 and 4)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
GREY = "#c9c8c2"          # background lines for the other vintages
TEXT = "#0b0b0b"
TEXT_SOFT = "#52514e"
GRID = "#e4e3df"
BACKGROUND = "#fcfcfb"

if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run Steps 1 and 2 first.")
    raise SystemExit

con = duckdb.connect(str(DATABASE_FILE), read_only=True)

# ---------------------------------------------------------------------------
# 1. Vintage curves in "long" form: one row per vintage per age
#    (easier to draw than the wide table in the SQL file)
# ---------------------------------------------------------------------------
curves = con.execute(
    f"""
    WITH loan_ages AS (
        SELECT
            approval_year,
            is_default,
            date_diff('month', approval_date, charge_off_date) AS months_to_chargeoff
        FROM loans_clean
        WHERE approval_year BETWEEN 2001 AND 2013
    ),
    ages AS (
        SELECT age FROM range(1, 14) AS t(age)      -- ages 1 to 13 years
    )
    SELECT
        l.approval_year                                      AS vintage,
        a.age                                                AS loan_age_years,
        100.0 * COUNT(*) FILTER (WHERE l.is_default = 1
                                   AND l.months_to_chargeoff < 12 * a.age)
              / COUNT(*)                                     AS cumulative_chargeoff_pct
    FROM loan_ages AS l
    CROSS JOIN ages AS a
    WHERE l.approval_year + a.age <= {DATA_YEAR}             -- only ages the vintage has reached
    GROUP BY l.approval_year, a.age
    ORDER BY l.approval_year, a.age
    """
).df()
curves["cumulative_chargeoff_pct"] = curves["cumulative_chargeoff_pct"].round(2)

# ---------------------------------------------------------------------------
# 2. Yearly roll-forward (same logic as Q2 in sql/05_roll_forward.sql)
# ---------------------------------------------------------------------------
roll = con.execute(
    """
    WITH loan_lives AS (
        SELECT
            YEAR(approval_date) AS start_year,
            is_default,
            CASE WHEN is_default = 1 THEN YEAR(charge_off_date)
                 ELSE YEAR(approval_date + term_months * INTERVAL 1 MONTH) END AS end_year
        FROM loans_clean
        WHERE approval_year >= 2001
          AND term_months > 0
          AND NOT (is_default = 1 AND charge_off_date IS NULL)
    )
    SELECT
        y.calendar_year,
        COUNT(*) FILTER (WHERE start_year < calendar_year AND end_year >= calendar_year) AS loans_at_start,
        COUNT(*) FILTER (WHERE start_year = calendar_year)                               AS new_loans,
        COUNT(*) FILTER (WHERE end_year = calendar_year AND is_default = 1)              AS charged_off,
        COUNT(*) FILTER (WHERE end_year = calendar_year AND is_default = 0)              AS paid_off,
        COUNT(*) FILTER (WHERE start_year <= calendar_year AND end_year > calendar_year) AS loans_at_end
    FROM range(2001, 2015) AS y(calendar_year)
    CROSS JOIN loan_lives
    GROUP BY y.calendar_year
    ORDER BY y.calendar_year
    """
).df()
con.close()

# The yearly rate. 2001 has no loans "at start" (we only follow loans from 2001
# onwards), so we leave that year empty instead of dividing by zero.
roll["annual_chargeoff_rate_pct"] = (
    100 * roll["charged_off"] / roll["loans_at_start"].where(roll["loans_at_start"] > 0)
).round(2)

curves.to_csv(OUTPUT_FOLDER / "vintage_curves.csv", index=False)
roll.to_csv(OUTPUT_FOLDER / "roll_forward.csv", index=False)
print("Saved outputs/vintage_curves.csv and outputs/roll_forward.csv")


def tidy_axes(ax):
    ax.set_facecolor(BACKGROUND)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(TEXT_SOFT)
    ax.tick_params(colors=TEXT_SOFT, labelsize=9, length=0)


# ---------------------------------------------------------------------------
# 3. Chart 1: vintage curves
#    Grey lines = every vintage. Blue and orange = the two we compare.
#    Each highlighted line is labelled at its end, so no legend box is needed.
# ---------------------------------------------------------------------------
figure, ax = plt.subplots(figsize=(10, 5.5))
figure.patch.set_facecolor(BACKGROUND)

for vintage, one_vintage in curves.groupby("vintage"):
    if vintage in (CALM_VINTAGE, CRISIS_VINTAGE):
        continue                                   # drawn on top, below
    ax.plot(one_vintage["loan_age_years"], one_vintage["cumulative_chargeoff_pct"],
            color=GREY, linewidth=1.2)

for vintage, colour in [(CALM_VINTAGE, BLUE), (CRISIS_VINTAGE, ORANGE)]:
    one_vintage = curves[curves["vintage"] == vintage]
    if one_vintage.empty:
        continue
    ax.plot(one_vintage["loan_age_years"], one_vintage["cumulative_chargeoff_pct"],
            color=colour, linewidth=2.5, marker="o", markersize=5)
    last = one_vintage.iloc[-1]                    # the last point of the line
    ax.annotate(f"{vintage} loans: {last['cumulative_chargeoff_pct']:.1f}%",
                xy=(last["loan_age_years"], last["cumulative_chargeoff_pct"]),
                xytext=(8, 0), textcoords="offset points", va="center",
                fontsize=10, color=TEXT, fontweight="bold")

tidy_axes(ax)
ax.set_xlabel("Loan age (years since approval)", color=TEXT_SOFT, fontsize=9)
ax.set_ylabel("% of the vintage charged off so far", color=TEXT_SOFT, fontsize=9)
ax.set_xlim(0.5, curves["loan_age_years"].max() + 2.5)   # room for the end labels
figure.suptitle("Vintage curves: how fast each year's loans went bad",
                x=0.01, ha="left", fontsize=13, color=TEXT, fontweight="bold")
ax.set_title("Each grey line is one approval year, 2001-2013. Lines stop at the age "
             f"each vintage had reached by {DATA_YEAR}.",
             loc="left", fontsize=9, color=TEXT_SOFT)
figure.tight_layout()
figure.savefig(OUTPUT_FOLDER / "vintage_curves.png", dpi=150)
plt.close(figure)
print("Saved outputs/vintage_curves.png")

# ---------------------------------------------------------------------------
# 4. Chart 2: annual charge-off rate by calendar year
# ---------------------------------------------------------------------------
rates = roll.dropna(subset=["annual_chargeoff_rate_pct"])
figure, ax = plt.subplots(figsize=(10, 4.2))
figure.patch.set_facecolor(BACKGROUND)
ax.bar(rates["calendar_year"], rates["annual_chargeoff_rate_pct"], width=0.8,
       color=BLUE, edgecolor=BACKGROUND, linewidth=1.5)
peak = rates.loc[rates["annual_chargeoff_rate_pct"].idxmax()]
ax.annotate(f"{peak['annual_chargeoff_rate_pct']:.1f}%",
            xy=(peak["calendar_year"], peak["annual_chargeoff_rate_pct"]),
            xytext=(0, 4), textcoords="offset points", ha="center",
            fontsize=9, color=TEXT, fontweight="bold")
tidy_axes(ax)
ax.set_xticks(rates["calendar_year"])
ax.set_ylabel("% of outstanding loans", color=TEXT_SOFT, fontsize=9)
figure.suptitle("Annual charge-off rate: share of outstanding loans charged off each year",
                x=0.01, ha="left", fontsize=12, color=TEXT, fontweight="bold")
ax.set_title("Loans approved from 2001. Slightly understated, because loans repaid "
             "early are counted until their scheduled end date.",
             loc="left", fontsize=9, color=TEXT_SOFT)
figure.tight_layout()
figure.savefig(OUTPUT_FOLDER / "annual_chargeoff_rate.png", dpi=150)
plt.close(figure)
print("Saved outputs/annual_chargeoff_rate.png")

print("\nDone! Open the outputs folder to look at the two charts.")
