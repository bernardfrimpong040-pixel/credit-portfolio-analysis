"""
Run a SQL file against our loan database and print each answer.

How to use it:
    python scripts/run_sql.py sql/01_first_look.sql

How it works:
  - It reads the .sql file you give it.
  - It splits the file into separate queries wherever there is a semicolon ( ; ).
  - It runs each query and prints the result as a table.
  - The comment line starting with "-- Q" above each query is printed as a title,
    so you can tell which answer belongs to which question.
"""

import sys                 # sys.argv lets us read what you typed after the script name
from pathlib import Path
import duckdb
import pandas as pd

# Show all columns and wider tables when printing
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)

PROJECT_FOLDER = Path(__file__).parent.parent
DATABASE_FILE = PROJECT_FOLDER / "data" / "loans.duckdb"

# --- 1. Check you told us which SQL file to run ----------------------------
if len(sys.argv) < 2:
    print("Please tell me which SQL file to run, for example:")
    print("    python scripts/run_sql.py sql/01_first_look.sql")
    raise SystemExit

sql_file = Path(sys.argv[1])
if not sql_file.exists():
    print("I can't find this file:", sql_file)
    raise SystemExit

if not DATABASE_FILE.exists():
    print("The database doesn't exist yet. Run  python scripts/01_load_data.py  first.")
    raise SystemExit

# --- 2. Read the file and split it into separate queries -------------------
all_text = sql_file.read_text(encoding="utf-8")
queries = [q.strip() for q in all_text.split(";") if q.strip()]

# --- 3. Connect (read_only=True means we can't accidentally change data) ----
con = duckdb.connect(str(DATABASE_FILE), read_only=True)

for query in queries:
    # Find the title line (the line starting with "-- Q") to print above the answer
    title_lines = [line for line in query.splitlines() if line.strip().startswith("-- Q")]
    title = title_lines[0].replace("--", "").strip() if title_lines else "Query"

    # Skip blocks that are only comments (no actual SQL)
    code_lines = [line for line in query.splitlines()
                  if line.strip() and not line.strip().startswith("--")]
    if not code_lines:
        continue

    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    try:
        result = con.execute(query).df()
        print(result.to_string(index=False))
    except duckdb.Error as problem:
        print("This query had a problem:", problem)

con.close()
