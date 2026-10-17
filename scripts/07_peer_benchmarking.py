"""
STEP 7b - Peer benchmarking tables and chart
============================================

What this script does, in plain words:
  1. Compares every lender and every state with its peers FAIRLY: against
     what peers achieved on the same kind of loans (same approval year,
     same loan size, same industry). See sql/07_peer_benchmarking.sql for
     the full explanation of "actual vs expected".
  2. Saves the results to  outputs/lender_benchmark.csv  and
     outputs/state_benchmark.csv
  3. Draws  outputs/lender_benchmark.png : for the 15 largest lenders and
     KeyBank, the RAW index (unfair) and the FAIR index side by side, so you
     can see how much the fair comparison changes the picture.

How to run it:
    python scripts/07_peer_benchmarking.py
"""

from pathlib import Path
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

PROJECT_FOLDER = Path(__file__).parent.parent
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"
OUTPUT_FOLDER = PROJECT_FOLDER / "outputs"
OUTPUT_FOLDER.mkdir(exist_ok=True)

FIRST_YEAR, LAST_YEAR = 2001, 2010
MINIMUM_LOANS = 300          # lenders with fewer loans are left out of the CSV (too noisy)
TOP_N = 15                   # how many of the largest lenders go in the chart
HIGHLIGHT = "KEYBANK"        # any lender name containing this is always shown

GREY = "#a3a29c"             # raw (unfair) index
BLUE = "#2a78d6"             # fair index
TEXT = "#0b0b0b"
TEXT_SOFT = "#52514e"
GRID = "#e4e3df"
BACKGROUND = "#fcfcfb"

if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run Steps 1 and 2 first.")
    raise SystemExit

con = duckdb.connect(str(DATABASE_FILE), read_only=True)


def benchmark(group_column):
    """Actual vs expected for any grouping, e.g. 'lender' or 'state'.
    Returns one row per group, largest (by dollars) first."""
    return con.execute(
        f"""
        WITH w AS (
            SELECT *, COALESCE({group_column}, 'Not recorded') AS group_name
            FROM loans_clean
            WHERE approval_year BETWEEN {FIRST_YEAR} AND {LAST_YEAR}
        ),
        boxes AS (
            SELECT approval_year, loan_size_band, sector_name,
                   AVG(is_default)                           AS peer_default_rate,
                   SUM(charge_off_amount) / SUM(loan_amount) AS peer_loss_rate
            FROM w
            GROUP BY approval_year, loan_size_band, sector_name
        ),
        scored AS (
            SELECT w.group_name, w.loan_amount, w.is_default, w.charge_off_amount,
                   b.peer_default_rate                AS expected_default,
                   b.peer_loss_rate * w.loan_amount   AS expected_loss
            FROM w JOIN boxes AS b USING (approval_year, loan_size_band, sector_name)
        ),
        portfolio AS (SELECT AVG(is_default) AS portfolio_rate FROM w)
        SELECT
            s.group_name,
            COUNT(*)                                            AS number_of_loans,
            SUM(s.loan_amount)                                  AS dollars,
            AVG(s.loan_amount)                                  AS average_loan,
            SUM(s.is_default)                                   AS actual_defaults,
            SUM(s.expected_default)                             AS expected_defaults,
            100.0 * AVG(s.is_default)                           AS actual_default_pct,
            100.0 * AVG(s.expected_default)                     AS expected_default_pct,
            AVG(s.is_default) / ANY_VALUE(p.portfolio_rate)     AS raw_index,
            SUM(s.is_default) / SUM(s.expected_default)         AS performance_index,
            SUM(s.charge_off_amount) / SUM(s.expected_loss)     AS loss_index
        FROM scored AS s CROSS JOIN portfolio AS p
        WHERE s.group_name <> 'Not recorded'
        GROUP BY s.group_name
        ORDER BY dollars DESC
        """
    ).df()


def add_verdict(table):
    """'Worse' / 'Better' only when the gap is bigger than 2 x square root of
    expected (the rule of thumb explained in the SQL file)."""
    gap = table["actual_defaults"] - table["expected_defaults"]
    limit = 2 * table["expected_defaults"] ** 0.5
    table["verdict"] = "In line with peers"
    table.loc[gap > limit, "verdict"] = "Worse than peers"
    table.loc[gap < -limit, "verdict"] = "Better than peers"
    return table


lenders = add_verdict(benchmark("lender"))
states = add_verdict(benchmark("state"))
con.close()

lenders.insert(0, "size_rank", range(1, len(lenders) + 1))
rounding = {"dollars": 0, "average_loan": 0, "expected_defaults": 1,
            "actual_default_pct": 1, "expected_default_pct": 1,
            "raw_index": 2, "performance_index": 2, "loss_index": 2}

lenders[lenders["number_of_loans"] >= MINIMUM_LOANS].round(rounding).to_csv(
    OUTPUT_FOLDER / "lender_benchmark.csv", index=False)
states.round(rounding).to_csv(OUTPUT_FOLDER / "state_benchmark.csv", index=False)
print("Saved outputs/lender_benchmark.csv and outputs/state_benchmark.csv")

# ---------------------------------------------------------------------------
# The chart: 15 largest lenders, plus KeyBank if it isn't already in them
# ---------------------------------------------------------------------------
is_highlight = lenders["group_name"].str.upper().str.contains(HIGHLIGHT)
chart = lenders[(lenders["size_rank"] <= TOP_N) | is_highlight].copy()
chart = chart.sort_values("performance_index")       # best at the bottom, worst at the top

columns_to_show = ["size_rank", "group_name", "number_of_loans", "raw_index",
                   "performance_index", "loss_index", "verdict"]
print(f"\nThe {TOP_N} largest lenders (and {HIGHLIGHT.title()}):")
print(chart.sort_values("size_rank")[columns_to_show].round(2).to_string(index=False))

figure, ax = plt.subplots(figsize=(10, 0.45 * len(chart) + 1.8))
figure.patch.set_facecolor(BACKGROUND)
positions = list(range(len(chart)))

# A thin line joins each lender's raw and fair index, so you can see the shift
ax.hlines(positions, chart["raw_index"], chart["performance_index"],
          color=GRID, linewidth=3, zorder=1)
ax.scatter(chart["raw_index"], positions, s=55, color=GREY, zorder=2)
ax.scatter(chart["performance_index"], positions, s=70, color=BLUE, zorder=3)

# The peer average line at 1.0
ax.axvline(1.0, color=TEXT_SOFT, linewidth=1, linestyle="--", zorder=0)
ax.annotate("Peer average = 1.0", xy=(1.0, len(chart) - 0.3), xytext=(4, 0),
            textcoords="offset points", fontsize=8, color=TEXT_SOFT, va="bottom")

# Lender names on the left; the highlighted lender in bold
labels = [f"{name.title()}  ({rank})" for name, rank in
          zip(chart["group_name"], chart["size_rank"])]
ax.set_yticks(positions)
ax.set_yticklabels(labels, fontsize=8.5, color=TEXT)
for tick, name in zip(ax.get_yticklabels(), chart["group_name"]):
    if HIGHLIGHT in name.upper():
        tick.set_fontweight("bold")

ax.set_facecolor(BACKGROUND)
ax.grid(axis="x", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
for side in ["top", "right", "left", "bottom"]:
    ax.spines[side].set_visible(False)
ax.tick_params(colors=TEXT_SOFT, labelsize=9, length=0)
ax.set_xlabel("Index (1.0 = same as peers; above 1 = more defaults)",
              color=TEXT_SOFT, fontsize=9)
ax.set_ylim(-0.7, len(chart) + 0.3)

legend_items = [
    Line2D([], [], marker="o", linestyle="", color=GREY, markersize=7,
           label="Raw: default rate vs whole portfolio (unfair)"),
    Line2D([], [], marker="o", linestyle="", color=BLUE, markersize=8,
           label="Fair: actual vs expected on the same kind of loans"),
]
ax.legend(handles=legend_items, loc="lower right", fontsize=8.5, frameon=True,
          facecolor=BACKGROUND, edgecolor=BACKGROUND, labelcolor=TEXT_SOFT)

figure.suptitle("Peer benchmarking: largest lenders, before and after a fair comparison",
                x=0.01, ha="left", fontsize=12, color=TEXT, fontweight="bold")
ax.set_title(f"Loans approved {FIRST_YEAR}-{LAST_YEAR}. Size rank in brackets. "
             "Fair = compared on the same approval year, loan size and industry.",
             loc="left", fontsize=8.5, color=TEXT_SOFT)
figure.tight_layout()
figure.savefig(OUTPUT_FOLDER / "lender_benchmark.png", dpi=150)
plt.close(figure)
print("\nSaved outputs/lender_benchmark.png")
print("\nDone!")
