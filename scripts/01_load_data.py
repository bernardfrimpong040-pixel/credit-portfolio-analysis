"""
STEP 1 - Load the SBA loan data into a database
================================================

What this script does, in plain words:
  1. Finds every CSV file you put in the folder  data/raw/
     (either SBAnational.csv from Kaggle, or the FOIA files from data.sba.gov)
  2. Reads them all into ONE table called  loans_raw  (everything kept as text,
     exactly as it is in the files, so nothing gets lost)
  3. Builds a second table called  loans  with only the columns we need,
     turned into proper numbers and dates so we can do maths on them
  4. Prints a short summary so you can check it worked

How to run it (in the VS Code terminal, with (.venv) showing):
    python scripts/01_load_data.py

You only need to run it again if you download new data.
"""

# ---------------------------------------------------------------------------
# 1. Import the tools we need
# ---------------------------------------------------------------------------
from pathlib import Path   # Path helps us work with folders and file names
import duckdb              # DuckDB is our SQL database (it lives in one file)

# ---------------------------------------------------------------------------
# 2. Tell Python where things are
# ---------------------------------------------------------------------------
# __file__ is this script. .parent is the "scripts" folder.
# .parent again is the main project folder.
PROJECT_FOLDER = Path(__file__).parent.parent
RAW_FOLDER = PROJECT_FOLDER / "data" / "raw"          # where your CSVs are
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"  # the database we create

# ---------------------------------------------------------------------------
# 3. Check that the CSV files are there
# ---------------------------------------------------------------------------
# .glob("*.csv") means "give me every file whose name ends in .csv"
csv_files = sorted(RAW_FOLDER.glob("*.csv"))

if len(csv_files) == 0:
    print("I could not find any CSV files in:", RAW_FOLDER)
    print("Download the SBA 7(a) files first (see GUIDE_STEP1.md), then run me again.")
    raise SystemExit  # stop the script here

print("Found these CSV files:")
for file in csv_files:
    size_mb = file.stat().st_size / 1_000_000   # file size in megabytes
    print(f"   {file.name}   ({size_mb:.0f} MB)")

# ---------------------------------------------------------------------------
# 4. Open (or create) the database file
# ---------------------------------------------------------------------------
con = duckdb.connect(str(DATABASE_FILE))   # "con" is short for connection

# ---------------------------------------------------------------------------
# 5. Read all the CSV files into one raw table
# ---------------------------------------------------------------------------
# Options explained:
#   all_varchar=true      -> read every column as text for now (safest)
#   normalize_names=true  -> make column names lower-case, e.g. GrossApproval -> grossapproval
#   union_by_name=true    -> stack the files on top of each other by matching column names
#   filename=true         -> add a column saying which file each row came from
print("\nReading the CSV files into the database. This can take a minute or two...")

# The SBA files are usually plain UTF-8 text. A few years used an older text
# format (latin-1). We try UTF-8 first and, if that fails, try latin-1.
file_list = [str(f) for f in csv_files]
for text_format in ["utf-8", "latin-1"]:
    try:
        con.execute(
            f"""
            CREATE OR REPLACE TABLE loans_raw AS
            SELECT *
            FROM read_csv({file_list},
                          all_varchar = true,
                          normalize_names = true,
                          union_by_name = true,
                          filename = true,
                          encoding = '{text_format}')
            """
        )
        print(f"   Read the files using the {text_format} text format.")
        break   # it worked, so leave the loop
    except duckdb.Error as problem:
        print(f"   The {text_format} format did not work, trying the next one...")
        last_problem = problem
else:
    # This 'else' runs only if the loop never hit 'break' (both formats failed)
    print("\nI could not read the files. Copy this message and send it to Claude:")
    print(last_problem)
    raise SystemExit

row_count = con.execute("SELECT COUNT(*) FROM loans_raw").fetchone()[0]
print(f"   loans_raw has {row_count:,} rows.")

# ---------------------------------------------------------------------------
# 6. Work out which version of the SBA data you downloaded
# ---------------------------------------------------------------------------
# There are two versions of the same SBA loan records:
#   - "kaggle":   one file called SBAnational.csv (loans approved up to 2014)
#   - "sba_site": the newer files from data.sba.gov (FOIA - 7(a) ... .csv)
# They use different column names, so we check which one we have.
columns_in_table = [row[0] for row in con.execute("DESCRIBE loans_raw").fetchall()]

if "mis_status" in columns_in_table and "loanstatus" in columns_in_table:
    print("\ndata/raw has BOTH versions of the data mixed together.")
    print("Keep only one version in data/raw (I suggest SBAnational.csv), then run me again.")
    raise SystemExit
elif "mis_status" in columns_in_table:
    data_version = "kaggle"
else:
    data_version = "sba_site"
print(f"   Data version detected: {data_version}")

# These are the columns each version must have for our analysis.
kaggle_needed_columns = [
    "state",            # state where the borrower is
    "bank",             # the lender (the bank that made the loan)
    "grappv",           # gross amount approved by the bank, in dollars
    "sba_appv",         # part of the loan the SBA guarantees
    "approvaldate",     # date the loan was approved, like 28-Feb-97
    "approvalfy",       # fiscal year of approval
    "term",             # how long the loan lasts, in months
    "naics",            # industry code (0 means "not recorded")
    "mis_status",       # "P I F" = paid in full, "CHGOFF" = charged off
    "chgoffdate",       # date the loan was written off as a loss
    "chgoffpringr",     # dollars lost when the loan was charged off
]

# ---------------------------------------------------------------------------
# 7. Check the columns we need are present
# ---------------------------------------------------------------------------
# These are the columns from the SBA data dictionary that our analysis uses.
needed_columns = [
    "borrstate",            # state where the borrower is
    "bankname",             # the lender (the bank that made the loan)
    "grossapproval",        # loan amount approved, in dollars
    "sbaguaranteedapproval",# part of the loan the SBA guarantees
    "approvaldate",         # date the loan was approved
    "approvalfiscalyear",   # government fiscal year of approval
    "terminmonths",         # how long the loan lasts, in months
    "naicscode",            # industry code (NAICS)
    "naicsdescription",     # industry name
    "businesstype",         # corporation, individual, partnership
    "loanstatus",           # PIF = paid in full, CHGOFF = charged off, etc.
    "paidinfulldate",       # date the loan was fully repaid
    "chargeoffdate",        # date the loan was written off as a loss
    "grosschargeoffamount", # dollars lost when the loan was charged off
]

# Pick the right checklist for the version we have
if data_version == "kaggle":
    needed_columns = kaggle_needed_columns

missing = [c for c in needed_columns if c not in columns_in_table]

if missing:
    print("\nThese columns are missing:", missing)
    print("Columns the file actually has:", columns_in_table)
    print("Send this message to Claude so we can adjust the names.")
    raise SystemExit

# ---------------------------------------------------------------------------
# 8. Build the clean working table "loans"
# ---------------------------------------------------------------------------
# TRY_CAST turns text into a number; if the text isn't a number it gives NULL
#   (empty) instead of crashing.
# REPLACE removes "$" and "," because money is written like "$60,000.00".
# TRIM removes extra spaces at the start or end.
# try_strptime turns text into a real date. The format code tells it how to read:
#   '%m/%d/%Y' reads 03/15/2012      '%d-%b-%y' reads 28-Feb-97
# Both versions end up with exactly the SAME clean columns, so every later
# script works the same no matter which version you downloaded.
print("\nBuilding the clean 'loans' table...")

kaggle_sql = """
    CREATE OR REPLACE TABLE loans AS
    SELECT
        row_number() OVER ()                                         AS loan_id,
        TRIM(state)                                                  AS state,
        TRIM(bank)                                                   AS lender,
        TRY_CAST(TRIM(REPLACE(REPLACE(grappv, '$', ''), ',', '')) AS DOUBLE)
                                                                     AS loan_amount,
        TRY_CAST(TRIM(REPLACE(REPLACE(sba_appv, '$', ''), ',', '')) AS DOUBLE)
                                                                     AS sba_guaranteed_amount,
        CAST(try_strptime(approvaldate, '%d-%b-%y') AS DATE)         AS approval_date,
        -- a few years are written like "1976A", so we keep just the 4 digits
        TRY_CAST(regexp_extract(approvalfy, '[0-9]{4}') AS INTEGER)  AS approval_year,
        TRY_CAST(term AS INTEGER)                                    AS term_months,
        NULLIF(TRIM(naics), '0')                                     AS naics_code,
        LEFT(NULLIF(TRIM(naics), '0'), 2)                            AS naics_sector,
        CAST(NULL AS VARCHAR)                                        AS industry,
        CAST(NULL AS VARCHAR)                                        AS business_type,
        -- "P I F" becomes "PIF" by removing the spaces
        NULLIF(REPLACE(UPPER(TRIM(mis_status)), ' ', ''), '')        AS loan_status,
        CAST(NULL AS DATE)                                           AS paid_in_full_date,
        CAST(try_strptime(chgoffdate, '%d-%b-%y') AS DATE)           AS charge_off_date,
        COALESCE(TRY_CAST(TRIM(REPLACE(REPLACE(chgoffpringr, '$', ''), ',', '')) AS DOUBLE), 0)
                                                                     AS charge_off_amount,
        filename                                                     AS source_file
    FROM loans_raw
"""

sba_site_sql = """
    CREATE OR REPLACE TABLE loans AS
    SELECT
        row_number() OVER ()                                   AS loan_id,
        borrstate                                              AS state,
        bankname                                               AS lender,
        TRY_CAST(REPLACE(REPLACE(grossapproval, '$', ''), ',', '') AS DOUBLE)
                                                               AS loan_amount,
        TRY_CAST(REPLACE(REPLACE(sbaguaranteedapproval, '$', ''), ',', '') AS DOUBLE)
                                                               AS sba_guaranteed_amount,
        CAST(try_strptime(approvaldate, '%m/%d/%Y') AS DATE)   AS approval_date,
        TRY_CAST(approvalfiscalyear AS INTEGER)                AS approval_year,
        TRY_CAST(terminmonths AS INTEGER)                      AS term_months,
        naicscode                                              AS naics_code,
        LEFT(naicscode, 2)                                     AS naics_sector,
        naicsdescription                                       AS industry,
        businesstype                                           AS business_type,
        UPPER(TRIM(loanstatus))                                AS loan_status,
        CAST(try_strptime(paidinfulldate, '%m/%d/%Y') AS DATE) AS paid_in_full_date,
        CAST(try_strptime(chargeoffdate, '%m/%d/%Y') AS DATE)  AS charge_off_date,
        COALESCE(TRY_CAST(REPLACE(REPLACE(grosschargeoffamount, '$', ''), ',', '') AS DOUBLE), 0)
                                                               AS charge_off_amount,
        filename                                               AS source_file
    FROM loans_raw
"""

# Run the version that matches your data
if data_version == "kaggle":
    con.execute(kaggle_sql)
else:
    con.execute(sba_site_sql)

# ---------------------------------------------------------------------------
# 9. A small lookup table of industry names
# ---------------------------------------------------------------------------
# The first 2 digits of a NAICS code tell you the broad industry ("sector").
# This table turns those 2 digits into a readable name, e.g. 72 -> Accommodation & Food.
# (Some sectors have several codes, e.g. 31, 32 and 33 are all Manufacturing.)
con.execute(
    """
    CREATE OR REPLACE TABLE naics_sectors AS
    SELECT * FROM (VALUES
        ('11', 'Agriculture, Forestry, Fishing & Hunting'),
        ('21', 'Mining, Oil & Gas'),
        ('22', 'Utilities'),
        ('23', 'Construction'),
        ('31', 'Manufacturing'), ('32', 'Manufacturing'), ('33', 'Manufacturing'),
        ('42', 'Wholesale Trade'),
        ('44', 'Retail Trade'), ('45', 'Retail Trade'),
        ('48', 'Transportation & Warehousing'), ('49', 'Transportation & Warehousing'),
        ('51', 'Information'),
        ('52', 'Finance & Insurance'),
        ('53', 'Real Estate, Rental & Leasing'),
        ('54', 'Professional, Scientific & Technical Services'),
        ('55', 'Management of Companies'),
        ('56', 'Administrative & Support / Waste Management'),
        ('61', 'Educational Services'),
        ('62', 'Health Care & Social Assistance'),
        ('71', 'Arts, Entertainment & Recreation'),
        ('72', 'Accommodation & Food Services'),
        ('81', 'Other Services (repair, personal care, etc.)'),
        ('92', 'Public Administration')
    ) AS t(naics_sector, sector_name)
    """
)

# ---------------------------------------------------------------------------
# 10. Print a short summary so we know it worked
# ---------------------------------------------------------------------------
summary = con.execute(
    """
    SELECT
        COUNT(*)                       AS number_of_loans,
        MIN(approval_year)             AS first_year,
        MAX(approval_year)             AS last_year,
        ROUND(SUM(loan_amount) / 1e9, 1) AS total_approved_billions
    FROM loans
    """
).df()   # .df() turns the answer into a neat pandas table for printing

print("\nDone! Here is a quick summary of the 'loans' table:")
print(summary.to_string(index=False))
print(f"\nDatabase saved to: {DATABASE_FILE}")

con.close()   # always close the database when finished
