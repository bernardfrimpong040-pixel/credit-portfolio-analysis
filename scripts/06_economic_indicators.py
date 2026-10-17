"""
STEP 6b - Economic indicators and early warning signals
=======================================================

What this script does, in plain words:
  1. Gets the U.S. unemployment rate (series UNRATE) from FRED, the free
     economic database of the Federal Reserve Bank of St. Louis
  2. Turns the monthly numbers into one average per year
  3. Puts it next to the portfolio's annual charge-off rate from Step 5
  4. Measures how closely the two move together (the "correlation"),
     in the same year and one year apart
  5. Builds two early warning signals, each Green / Amber / Red:
       - ECONOMY:   how much unemployment rose compared with the year before
       - PORTFOLIO: how fast each new vintage failed in its first 2 years,
                    compared with the calm 2001-2003 vintages
  6. Saves tables and two charts in  outputs/

How to run it:
    python scripts/06_economic_indicators.py

You need to have run Step 5 first (it makes outputs/roll_forward.csv).
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
EXTERNAL_FOLDER = PROJECT_FOLDER / "data" / "external"     # outside data lives here
UNEMPLOYMENT_FILE = EXTERNAL_FOLDER / "UNRATE.csv"
FRED_DOWNLOAD_LINK = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE"

FIRST_YEAR, LAST_YEAR = 2001, 2014

# Signal settings (example values for this project - change and re-run)
UNEMPLOYMENT_RISE_AMBER = 1.0   # unemployment up 1+ percentage point on last year -> Amber
UNEMPLOYMENT_RISE_RED = 2.0     # up 2+ points -> Red
VINTAGE_AMBER = 2.0             # new vintage failing 2x as fast as normal -> Amber
VINTAGE_RED = 3.0               # 3x as fast -> Red

# Colours. Green/Amber/Red use fixed "status" colours, and every coloured mark
# also gets a text label, so the meaning never depends on colour alone.
BLUE = "#2a78d6"
STATUS_COLOURS = {"Green": "#0ca30c", "Amber": "#fab219", "Red": "#d03b3b"}
TEXT = "#0b0b0b"
TEXT_SOFT = "#52514e"
GRID = "#e4e3df"
BACKGROUND = "#fcfcfb"

OUTPUT_FOLDER.mkdir(exist_ok=True)
EXTERNAL_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Get the unemployment data
#    If we already have the file, use it. If not, download it from FRED.
# ---------------------------------------------------------------------------
if not UNEMPLOYMENT_FILE.exists():
    print("Downloading the unemployment rate from FRED...")
    try:
        downloaded = pd.read_csv(FRED_DOWNLOAD_LINK)
        downloaded.to_csv(UNEMPLOYMENT_FILE, index=False)
        print(f"   saved to {UNEMPLOYMENT_FILE}")
    except Exception as problem:
        print("\nI couldn't download it automatically. Please do it by hand:")
        print(f"  1. Open this link in your browser: {FRED_DOWNLOAD_LINK}")
        print("  2. It downloads a file (often called UNRATE.csv or fredgraph.csv).")
        print(f"  3. Rename it UNRATE.csv and move it into: {EXTERNAL_FOLDER}")
        print("  4. Run this script again.")
        print("\n(The error was:", problem, ")")
        raise SystemExit

unemployment = pd.read_csv(UNEMPLOYMENT_FILE)
# FRED has used different column names over the years ("DATE" or
# "observation_date"), so we use the column POSITIONS instead:
# the first column is the date, the second is the value.
unemployment.columns = ["date", "unemployment_rate"]
unemployment["date"] = pd.to_datetime(unemployment["date"])
# FRED writes "." for a missing value; errors="coerce" turns that into empty
unemployment["unemployment_rate"] = pd.to_numeric(unemployment["unemployment_rate"],
                                                  errors="coerce")

# One average per calendar year (we need 1 year earlier for the "rise")
unemployment["year"] = unemployment["date"].dt.year
yearly = (unemployment[unemployment["year"].between(FIRST_YEAR - 1, LAST_YEAR)]
          .groupby("year", as_index=False)["unemployment_rate"].mean())
yearly["unemployment_rate"] = yearly["unemployment_rate"].round(2)

# How much unemployment rose (or fell) compared with the year before
yearly["unemployment_change"] = yearly["unemployment_rate"].diff().round(2)

# ---------------------------------------------------------------------------
# 2. Join it to the portfolio's annual charge-off rate from Step 5
# ---------------------------------------------------------------------------
roll_forward_file = OUTPUT_FOLDER / "roll_forward.csv"
if not roll_forward_file.exists():
    print("I can't find outputs/roll_forward.csv. Run Step 5 first:")
    print("    python scripts/05_roll_forward_charts.py")
    raise SystemExit

roll = pd.read_csv(roll_forward_file)[["calendar_year", "annual_chargeoff_rate_pct"]]
roll = roll.rename(columns={"calendar_year": "year"})

economy = yearly.merge(roll, on="year", how="inner")   # keep years found in both

# The economy signal for each year
def economy_signal(change):
    if pd.isna(change):
        return ""
    if change >= UNEMPLOYMENT_RISE_RED:
        return "Red"
    if change >= UNEMPLOYMENT_RISE_AMBER:
        return "Amber"
    return "Green"

economy["economy_signal"] = economy["unemployment_change"].apply(economy_signal)

# ---------------------------------------------------------------------------
# 3. Correlation: do unemployment and charge-offs move together?
#    A correlation is between -1 and +1:
#       +1  = they always rise and fall together
#        0  = no connection
#       -1  = one rises when the other falls
#    "One year apart" compares LAST year's unemployment with THIS year's
#    charge-off rate, to test whether unemployment moves first.
# ---------------------------------------------------------------------------
# 2001 has no proper charge-off rate (Step 5 tracks loans from 2001), so we
# start from 2002.
study = economy[economy["year"] >= 2002].copy()
study["unemployment_last_year"] = study["unemployment_rate"].shift(1)
# shift(1) moves the column down one row, so each row sees last year's value.
# The first row then has no "last year", so that comparison uses one year fewer.

same_year = study["unemployment_rate"].corr(study["annual_chargeoff_rate_pct"])
one_year_apart = study["unemployment_last_year"].corr(study["annual_chargeoff_rate_pct"])
years_used = len(study)

print("\nHow closely unemployment and the charge-off rate move together")
print(f"   (years {study['year'].min()}-{study['year'].max()}, {years_used} years)")
print(f"   same year:                              {same_year:+.2f}")
print(f"   unemployment one year BEFORE charge-offs: {one_year_apart:+.2f}")

economy.to_csv(OUTPUT_FOLDER / "economic_indicators.csv", index=False)
print("\nSaved outputs/economic_indicators.csv")
print(economy.to_string(index=False))

# ---------------------------------------------------------------------------
# 4. The portfolio early warning: how fast each new vintage failed in its
#    first 2 years, compared with the calm 2001-2003 vintages
#    (same logic as Q1 in sql/06_early_warnings.sql)
# ---------------------------------------------------------------------------
if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run Steps 1 and 2 first.")
    raise SystemExit

con = duckdb.connect(str(DATABASE_FILE), read_only=True)
vintages = con.execute(
    """
    SELECT
        approval_year AS vintage,
        approval_year + 2 AS year_known,
        100.0 * COUNT(*) FILTER (WHERE is_default = 1
              AND date_diff('month', approval_date, charge_off_date) < 24)
              / COUNT(*) AS age_2_pct
    FROM loans_clean
    WHERE approval_year BETWEEN 2001 AND 2012
    GROUP BY approval_year
    ORDER BY approval_year
    """
).df()
con.close()

baseline = vintages.loc[vintages["vintage"].between(2001, 2003), "age_2_pct"].mean()
vintages["times_baseline"] = (vintages["age_2_pct"] / baseline).round(1)
vintages["age_2_pct"] = vintages["age_2_pct"].round(2)

def vintage_signal(times):
    if times >= VINTAGE_RED:
        return "Red"
    if times >= VINTAGE_AMBER:
        return "Amber"
    return "Green"

vintages["portfolio_signal"] = vintages["times_baseline"].apply(vintage_signal)
vintages.to_csv(OUTPUT_FOLDER / "early_warning_signals.csv", index=False)
print(f"\nPortfolio early warning (baseline = {baseline:.2f}% charged off within 2 years)")
print(vintages.to_string(index=False))
print("Saved outputs/early_warning_signals.csv")

# The year the loss rate peaked, used as a marker on the charts
peak_year = int(economy.loc[economy["annual_chargeoff_rate_pct"].idxmax(), "year"])


def tidy_axes(ax):
    ax.set_facecolor(BACKGROUND)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(TEXT_SOFT)
    ax.tick_params(colors=TEXT_SOFT, labelsize=9, length=0)


# ---------------------------------------------------------------------------
# 5. Chart 1: unemployment (top) and charge-off rate (bottom), same years.
#    Two separate panels, because the two numbers measure different things.
# ---------------------------------------------------------------------------
figure, (top, bottom) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
figure.patch.set_facecolor(BACKGROUND)

top.plot(economy["year"], economy["unemployment_rate"], color=BLUE, linewidth=2)
for _, row in economy.iterrows():
    if row["economy_signal"] in ("Amber", "Red"):          # mark only the warnings
        top.scatter(row["year"], row["unemployment_rate"], s=90, zorder=3,
                    color=STATUS_COLOURS[row["economy_signal"]],
                    edgecolor=BACKGROUND, linewidth=2)
        top.annotate(f"{row['economy_signal']}: +{row['unemployment_change']:.1f} pts",
                     xy=(row["year"], row["unemployment_rate"]),
                     xytext=(-8, 8), textcoords="offset points", ha="right",
                     fontsize=9, color=TEXT)
tidy_axes(top)
top.set_title("U.S. unemployment rate (yearly average, %)", loc="left",
              fontsize=11, color=TEXT, fontweight="bold")

bottom.bar(economy["year"], economy["annual_chargeoff_rate_pct"], width=0.7,
           color=BLUE, edgecolor=BACKGROUND, linewidth=1.5)
peak_value = economy.loc[economy["year"] == peak_year, "annual_chargeoff_rate_pct"].iloc[0]
bottom.annotate(f"Peak {peak_year}: {peak_value:.1f}%", xy=(peak_year, peak_value),
                xytext=(0, 4), textcoords="offset points", ha="center",
                fontsize=9, color=TEXT, fontweight="bold")
tidy_axes(bottom)
bottom.set_title("Portfolio annual charge-off rate (% of outstanding loans, Step 5)",
                 loc="left", fontsize=11, color=TEXT, fontweight="bold")
bottom.set_xticks(economy["year"])

figure.suptitle("The economy vs portfolio losses, "
                f"{economy['year'].min()}-{economy['year'].max()}",
                x=0.01, ha="left", fontsize=13, color=TEXT, fontweight="bold")
figure.text(0.01, 0.005, "Sources: FRED series UNRATE (U.S. Bureau of Labor Statistics); "
            "SBA loan data via Kaggle.", fontsize=8, color=TEXT_SOFT)
figure.tight_layout(rect=(0, 0.02, 1, 0.97))
figure.savefig(OUTPUT_FOLDER / "economy_vs_chargeoffs.png", dpi=150)
plt.close(figure)
print("\nSaved outputs/economy_vs_chargeoffs.png")

# ---------------------------------------------------------------------------
# 6. Chart 2: the portfolio early warning, by the year it could be seen
# ---------------------------------------------------------------------------
figure, ax = plt.subplots(figsize=(10, 4.8))
figure.patch.set_facecolor(BACKGROUND)
ax.bar(vintages["year_known"], vintages["times_baseline"], width=0.7,
       color=[STATUS_COLOURS[s] for s in vintages["portfolio_signal"]],
       edgecolor=BACKGROUND, linewidth=1.5)
tallest = vintages["times_baseline"].max()
ax.set_ylim(0, tallest * 1.25)                   # leave room at the top for labels
last_year = vintages["year_known"].max()
ax.set_xlim(vintages["year_known"].min() - 0.6, last_year + 1.8)   # room on the right

# Value and status above each bar. The small background box keeps the text
# readable where it crosses a dashed line.
for _, row in vintages.iterrows():
    ax.annotate(f"{row['times_baseline']:.1f}x\n{row['portfolio_signal']}",
                xy=(row["year_known"], row["times_baseline"]),
                xytext=(0, 3), textcoords="offset points", ha="center",
                fontsize=8, color=TEXT,
                bbox=dict(boxstyle="square,pad=0.1", facecolor=BACKGROUND, edgecolor="none"))

# The Amber and Red lines, labelled in the empty space on the right
# The lines stop just after the last bar; Red's label sits above its line and
# Amber's below, so the two never overlap.
for level, name, position in [(VINTAGE_AMBER, "Amber", "top"), (VINTAGE_RED, "Red", "bottom")]:
    ax.hlines(level, xmin=vintages["year_known"].min() - 0.6, xmax=last_year + 0.45,
              color=TEXT_SOFT, linewidth=0.8, linestyle="--", zorder=0)
    ax.annotate(f"{name} from {level:.0f}x", xy=(last_year + 0.5, level),
                ha="left", va=position, fontsize=8, color=TEXT_SOFT)

# A dotted line at the year losses peaked, labelled at the very top
ax.axvline(peak_year, color=TEXT, linewidth=1, linestyle=":", zorder=0)
ax.annotate(f"Loss peak ({peak_year}) ", xy=(peak_year, tallest * 1.22),
            ha="right", va="top", fontsize=9, color=TEXT)
tidy_axes(ax)
ax.set_xticks(vintages["year_known"])
ax.set_xticklabels([f"{k}\n({v} loans)" for k, v in
                    zip(vintages["year_known"], vintages["vintage"])], fontsize=8)
ax.set_xlabel("Year the signal could first be seen (vintage in brackets)",
              color=TEXT_SOFT, fontsize=9)
ax.set_ylabel("Times the normal 2-year failure rate", color=TEXT_SOFT, fontsize=9)
figure.suptitle("Early warning: how fast each new vintage failed in its first 2 years",
                x=0.01, ha="left", fontsize=12, color=TEXT, fontweight="bold")
ax.set_title(f"Normal = 2001-2003 vintages ({baseline:.2f}% charged off within 2 years).",
             loc="left", fontsize=9, color=TEXT_SOFT)
figure.tight_layout()
figure.savefig(OUTPUT_FOLDER / "early_warning_vintages.png", dpi=150)
plt.close(figure)
print("Saved outputs/early_warning_vintages.png")

print("\nDone!")
