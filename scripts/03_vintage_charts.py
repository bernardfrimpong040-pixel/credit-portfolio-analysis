"""
STEP 3b - Make the vintage charts
=================================

What this script does, in plain words:
  1. Asks the database for the vintage table (one row per approval year)
     and for the losses by charge-off year
  2. Saves both tables as CSV files in  outputs/  (you can open them in Excel,
     and we'll reuse them for the dashboard in Step 8)
  3. Draws two charts and saves them as PNG pictures in  outputs/ :
       - vintage_performance.png  : default rate and loss rate by approval year
       - losses_by_year.png       : dollars lost in each calendar year
     These pictures go into your README on GitHub.

How to run it:
    python scripts/03_vintage_charts.py
"""

from pathlib import Path
import duckdb
import matplotlib
matplotlib.use("Agg")          # draw straight to files, without opening a window
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

PROJECT_FOLDER = Path(__file__).parent.parent
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"
OUTPUT_FOLDER = PROJECT_FOLDER / "outputs"
OUTPUT_FOLDER.mkdir(exist_ok=True)

# The last vintage we treat as "seasoned" (old enough to judge). See Q1 of
# sql/03_vintage_analysis.sql for why: most defaults happen in the first few years.
LAST_SEASONED_YEAR = 2010

# Chart colours, kept in one place so every chart looks the same
BLUE = "#2a78d6"           # main colour for the bars
BLUE_LIGHT = "#a9c8ef"     # lighter blue for the "too young to judge" years
TEXT = "#0b0b0b"           # main text
TEXT_SOFT = "#52514e"      # axis labels and notes
GRID = "#e4e3df"           # faint grid lines
BACKGROUND = "#fcfcfb"     # chart background

if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run Steps 1 and 2 first.")
    raise SystemExit

con = duckdb.connect(str(DATABASE_FILE), read_only=True)

# ---------------------------------------------------------------------------
# 1. Get the two tables from the database
# ---------------------------------------------------------------------------
vintages = con.execute(
    f"""
    SELECT
        approval_year                                               AS vintage,
        CASE WHEN approval_year <= {LAST_SEASONED_YEAR} THEN 'Seasoned'
             ELSE 'Too young to judge' END                          AS seasoning,
        COUNT(*)                                                    AS number_of_loans,
        ROUND(SUM(loan_amount) / 1e6, 0)                            AS approved_millions,
        ROUND(100.0 * AVG(is_default), 1)                           AS default_rate_pct,
        ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 1) AS loss_rate_pct
    FROM loans_clean
    GROUP BY approval_year
    ORDER BY approval_year
    """
).df()

losses = con.execute(
    """
    SELECT
        YEAR(charge_off_date)                   AS charge_off_year,
        COUNT(*)                                AS loans_charged_off,
        ROUND(SUM(charge_off_amount) / 1e6, 0)  AS dollars_lost_millions
    FROM loans_clean
    WHERE is_default = 1
      AND charge_off_date IS NOT NULL
      AND YEAR(charge_off_date) BETWEEN 1989 AND 2014
    GROUP BY charge_off_year
    ORDER BY charge_off_year
    """
).df()
con.close()

# ---------------------------------------------------------------------------
# 2. Save the tables as CSV files
# ---------------------------------------------------------------------------
vintages.to_csv(OUTPUT_FOLDER / "vintage_performance.csv", index=False)
losses.to_csv(OUTPUT_FOLDER / "losses_by_year.csv", index=False)
print("Saved outputs/vintage_performance.csv and outputs/losses_by_year.csv")


# ---------------------------------------------------------------------------
# A small helper that gives every chart the same clean look
# ---------------------------------------------------------------------------
def tidy_axes(ax, y_label):
    ax.set_facecolor(BACKGROUND)
    ax.grid(axis="y", color=GRID, linewidth=0.8)   # faint horizontal lines only
    ax.set_axisbelow(True)                          # grid goes behind the bars
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)          # remove the box around the chart
    ax.spines["bottom"].set_color(TEXT_SOFT)
    ax.tick_params(colors=TEXT_SOFT, labelsize=9, length=0)
    ax.set_ylabel(y_label, color=TEXT_SOFT, fontsize=9)


def label_highest_bar(ax, x_values, y_values, suffix):
    """Write the value above the tallest bar only (not on every bar)."""
    position = y_values.idxmax()
    ax.annotate(
        f"{y_values[position]:,.1f}{suffix}" if suffix == "%" else f"${y_values[position]:,.0f}M",
        xy=(x_values[position], y_values[position]),
        xytext=(0, 4), textcoords="offset points",
        ha="center", va="bottom", fontsize=9, color=TEXT, fontweight="bold",
    )


# ---------------------------------------------------------------------------
# 3. Chart 1: default rate and loss rate by vintage (two panels, one above
#    the other, so each measure has its own scale)
# ---------------------------------------------------------------------------
bar_colours = [BLUE if s == "Seasoned" else BLUE_LIGHT for s in vintages["seasoning"]]
bar_hatches = ["" if s == "Seasoned" else "///" for s in vintages["seasoning"]]

figure, (top, bottom) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
figure.patch.set_facecolor(BACKGROUND)

panels = [
    (top, "default_rate_pct", "Default rate: % of loans charged off"),
    (bottom, "loss_rate_pct", "Loss rate: % of approved dollars lost"),
]
for ax, column, title in panels:
    bars = ax.bar(vintages["vintage"], vintages[column], width=0.8,
                  color=bar_colours, edgecolor=BACKGROUND, linewidth=1.5)
    for bar, hatch in zip(bars, bar_hatches):
        bar.set_hatch(hatch)
    tidy_axes(ax, "%")
    ax.set_title(title, loc="left", fontsize=11, color=TEXT, fontweight="bold")
    label_highest_bar(ax, vintages["vintage"], vintages[column], "%")

bottom.set_xticks(vintages["vintage"][::2])        # label every second year
bottom.set_xlabel("Approval year (vintage)", color=TEXT_SOFT, fontsize=9)

legend_items = [
    Patch(facecolor=BLUE, label="Seasoned (4+ years old in 2014)"),
    Patch(facecolor=BLUE_LIGHT, hatch="///", edgecolor=BACKGROUND,
          label="Too young to judge (2011-2014)"),
]
top.legend(handles=legend_items, loc="upper left", frameon=False, fontsize=9,
           labelcolor=TEXT_SOFT, bbox_to_anchor=(0, 0.92))

figure.suptitle("SBA 7(a) loans: performance by approval year, 1989-2014",
                x=0.01, ha="left", fontsize=13, color=TEXT, fontweight="bold")
total_loans = vintages["number_of_loans"].sum()     # add up the loans in every vintage
figure.text(0.01, 0.005,
            "Source: U.S. Small Business Administration loan data (via Kaggle), "
            f"{total_loans:,} loans after cleaning.",
            fontsize=8, color=TEXT_SOFT)
figure.tight_layout(rect=(0, 0.02, 1, 0.97))
figure.savefig(OUTPUT_FOLDER / "vintage_performance.png", dpi=150)
plt.close(figure)
print("Saved outputs/vintage_performance.png")

# ---------------------------------------------------------------------------
# 4. Chart 2: dollars lost in each calendar year
# ---------------------------------------------------------------------------
figure, ax = plt.subplots(figsize=(10, 4.5))
figure.patch.set_facecolor(BACKGROUND)
ax.bar(losses["charge_off_year"], losses["dollars_lost_millions"], width=0.8,
       color=BLUE, edgecolor=BACKGROUND, linewidth=1.5)
tidy_axes(ax, "$ millions")
label_highest_bar(ax, losses["charge_off_year"], losses["dollars_lost_millions"], "M")
ax.set_xticks(losses["charge_off_year"][::2])
ax.set_xlabel("Year the loan was charged off", color=TEXT_SOFT, fontsize=9)
ax.set_title("When the losses arrived: dollars charged off per year",
             loc="left", fontsize=13, color=TEXT, fontweight="bold")
figure.tight_layout()
figure.savefig(OUTPUT_FOLDER / "losses_by_year.png", dpi=150)
plt.close(figure)
print("Saved outputs/losses_by_year.png")

print("\nDone! Open the outputs folder to look at the two charts.")
