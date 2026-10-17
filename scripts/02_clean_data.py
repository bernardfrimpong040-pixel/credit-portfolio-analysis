"""
STEP 2b - Clean the loan data
=============================

What this script does, in plain words:
  1. Makes a copy of the 'loans' table called 'loans_clean'
  2. Removes rows we can't use, one rule at a time
  3. Writes down how many rows each rule removed (the "cleaning log").
     Banks call this an audit trail: anyone can see exactly what was
     removed and why.
  4. Adds a few helpful columns for the analysis in later steps
  5. Saves the cleaning log to  outputs/data_quality_log.csv

The original 'loans' table is NOT changed, so you can always go back.

How to run it (in the VS Code terminal, with (.venv) showing):
    python scripts/02_clean_data.py
"""

from pathlib import Path
import duckdb

PROJECT_FOLDER = Path(__file__).parent.parent
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"
OUTPUT_FOLDER = PROJECT_FOLDER / "outputs"

# The first approval year we keep. Before 1989 there are very few loans
# (about 1.6% of the data), too few to measure anything reliably.
START_YEAR = 1989

# ---------------------------------------------------------------------------
# 1. Connect to the database
# ---------------------------------------------------------------------------
if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run  python scripts/01_load_data.py  first.")
    raise SystemExit

con = duckdb.connect(str(DATABASE_FILE))

# ---------------------------------------------------------------------------
# 2. Start with a full copy of the loans table
# ---------------------------------------------------------------------------
con.execute("CREATE OR REPLACE TABLE loans_clean AS SELECT * FROM loans")
starting_rows = con.execute("SELECT COUNT(*) FROM loans_clean").fetchone()[0]
print(f"Starting with {starting_rows:,} loans.\n")

# ---------------------------------------------------------------------------
# 3. The cleaning rules
# ---------------------------------------------------------------------------
# Each rule has two parts:
#   - a plain-English reason (this goes into the cleaning log)
#   - a SQL condition describing the rows to REMOVE
cleaning_rules = [
    (
        f"Approved before {START_YEAR} (too few loans to measure reliably)",
        f"approval_year < {START_YEAR} OR approval_year IS NULL",
    ),
    (
        "No final status, or cancelled before any money was lent",
        "loan_status IS NULL OR loan_status = 'CANCLD'",
    ),
    (
        "Loan amount missing, zero or negative",
        "loan_amount IS NULL OR loan_amount <= 0",
    ),
]

# We collect one line of the log for each rule
log_rows = []
rows_now = starting_rows

for rule_number, (reason, remove_condition) in enumerate(cleaning_rules, start=1):
    # Count how many rows this rule will remove
    to_remove = con.execute(
        f"SELECT COUNT(*) FROM loans_clean WHERE {remove_condition}"
    ).fetchone()[0]

    # Remove them
    con.execute(f"DELETE FROM loans_clean WHERE {remove_condition}")

    rows_after = rows_now - to_remove
    log_rows.append((rule_number, reason, rows_now, to_remove, rows_after))
    print(f"Rule {rule_number}: {reason}")
    print(f"        removed {to_remove:,} rows, {rows_after:,} left\n")
    rows_now = rows_after

# ---------------------------------------------------------------------------
# 4. Tidy up and add helpful columns
# ---------------------------------------------------------------------------
# - state: make it upper case with no extra spaces (e.g. " oh" -> "OH")
# - is_default: 1 if the loan was charged off, 0 if not. Taking the AVERAGE of
#   this column gives the default rate directly, which we'll use a lot.
# - sector_name: the readable industry name (or "Not recorded")
# - loan_size_band: groups loan sizes into 5 bands for the concentration step
# - flag_...: TRUE/FALSE columns that mark odd rows. We keep these rows but
#   mark them, so we can decide later whether they affect any result.
print("Tidying columns and adding helpful new ones...")
con.execute(
    """
    CREATE OR REPLACE TABLE loans_clean AS
    SELECT
        l.* REPLACE (UPPER(TRIM(l.state)) AS state),

        CASE WHEN l.loan_status = 'CHGOFF' THEN 1 ELSE 0 END      AS is_default,

        COALESCE(s.sector_name, 'Not recorded')                    AS sector_name,

        CASE
            WHEN l.loan_amount <    50000 THEN '1. Under $50K'
            WHEN l.loan_amount <   150000 THEN '2. $50K-$150K'
            WHEN l.loan_amount <   350000 THEN '3. $150K-$350K'
            WHEN l.loan_amount <  1000000 THEN '4. $350K-$1M'
            ELSE                               '5. $1M and over'
        END                                                         AS loan_size_band,

        (l.loan_status = 'CHGOFF' AND l.charge_off_amount = 0)      AS flag_chgoff_no_loss,
        (l.charge_off_amount > l.loan_amount)                       AS flag_loss_over_amount,
        (l.loan_status = 'PIF' AND l.charge_off_amount > 0)         AS flag_pif_with_loss,
        (l.term_months = 0)                                         AS flag_zero_term
    FROM loans_clean AS l
    LEFT JOIN naics_sectors AS s
           ON l.naics_sector = s.naics_sector
    """
)

# ---------------------------------------------------------------------------
# 5. Save the cleaning log as a table and as a CSV file
# ---------------------------------------------------------------------------
con.execute(
    """
    CREATE OR REPLACE TABLE data_quality_log (
        rule_number   INTEGER,
        reason        VARCHAR,
        rows_before   BIGINT,
        rows_removed  BIGINT,
        rows_after    BIGINT
    )
    """
)
con.executemany("INSERT INTO data_quality_log VALUES (?, ?, ?, ?, ?)", log_rows)

OUTPUT_FOLDER.mkdir(exist_ok=True)   # make the outputs folder if it isn't there
log_file = OUTPUT_FOLDER / "data_quality_log.csv"
con.execute(f"COPY data_quality_log TO '{log_file.as_posix()}' (HEADER, DELIMITER ',')")

# ---------------------------------------------------------------------------
# 6. Final summary
# ---------------------------------------------------------------------------
summary = con.execute(
    """
    SELECT
        COUNT(*)                                     AS loans_kept,
        MIN(approval_year)                           AS first_year,
        MAX(approval_year)                           AS last_year,
        ROUND(SUM(loan_amount) / 1e9, 1)             AS approved_billions,
        ROUND(100.0 * AVG(is_default), 2)            AS percent_charged_off,
        COUNT(*) FILTER (WHERE flag_chgoff_no_loss)   AS flagged_chgoff_no_loss,
        COUNT(*) FILTER (WHERE flag_loss_over_amount) AS flagged_loss_over_amount,
        COUNT(*) FILTER (WHERE flag_pif_with_loss)    AS flagged_pif_with_loss,
        COUNT(*) FILTER (WHERE flag_zero_term)        AS flagged_zero_term
    FROM loans_clean
    """
).df()

# Check that the date problems from the quality checks (Q5) are gone.
# We expect 0 for both, because those were the 1960s loans removed by rule 1.
date_check = con.execute(
    """
    SELECT
        COUNT(*) FILTER (WHERE ABS(YEAR(approval_date) - approval_year) > 1)
                                                        AS dates_wrong_century_left,
        COUNT(*) FILTER (WHERE charge_off_date < approval_date)
                                                        AS chargeoff_before_approval_left
    FROM loans_clean
    """
).df()

percent_kept = 100 * rows_now / starting_rows
print(f"\nDone! Kept {rows_now:,} of {starting_rows:,} loans ({percent_kept:.1f}%).")
# Print each result on its own line, which is easier to read than one wide row
for column in summary.columns:
    value = summary[column][0]
    if column.endswith("year"):
        print(f"   {column:<28} {value}")      # years: no comma (2014, not 2,014)
    else:
        print(f"   {column:<28} {value:,}")    # other numbers: with commas

print("\nDate problems left after cleaning (we expect 0 for both):")
for column in date_check.columns:
    print(f"   {column:<32} {date_check[column][0]:,}")
print(f"\nCleaning log saved to: {log_file}")

con.close()
