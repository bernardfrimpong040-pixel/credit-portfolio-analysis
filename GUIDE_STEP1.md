# Step 1 Guide: Set up, download the data, and take a first look

You already have Python, VS Code, Git and GitHub Desktop from the retail project,
so this setup is short.

---

## A. Put the project folder in place

1. Unzip `credit-portfolio-analysis.zip` into the same place as your retail
   project, e.g. `Documents/projects/`.
2. In VS Code: **File → Open Folder…** → choose `credit-portfolio-analysis`.
3. Open a terminal: **Terminal → New Terminal**.

## B. Make a fresh Python environment (same steps that worked last time)

Run these lines **one at a time**:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

You should see `(.venv)` at the start of the terminal line.

## C. Download the loan data (by hand, in your browser)

1. Go to <https://data.sba.gov/dataset/7-a-504-foia>
2. Download these files (the "asof" date in the name changes every quarter,
   so just pick the newest one of each):
   - **FOIA - 7(a) (FY2010-FY2019) asof …csv** (about 250 MB)
   - **FOIA - 7(a) (FY2020-Present) asof …csv**
   - **the data dictionary** (it explains every column; keep it open while you work)
3. Move the two CSV files into the project folder `data/raw/`.
   (Create the `raw` folder inside `data` if it isn't there.)

Why 2010 onward? That gives us 15+ years of loans, including the COVID period,
which is exactly the kind of "emerging risk" event a credit team studies. It also
keeps the files a manageable size for a laptop.

## D. Build the database

```powershell
python scripts/01_load_data.py
```

It should end with "Done!" and a small summary table.
If it prints a message asking you to send it to Claude, copy the whole
terminal output and paste it to me.

## E. Run your first SQL questions

```powershell
python scripts/run_sql.py sql/01_first_look.sql
```

Before you run it, open `sql/01_first_look.sql` and guess each answer.
Then compare. Write down anything that surprises you.

## F. Save to GitHub

Open GitHub Desktop → **File → Add local repository…** → choose the
`credit-portfolio-analysis` folder → create the repository → commit with the
summary `Step 1: load SBA loan data` → **Publish repository** (public).

The data files will NOT upload. That's on purpose: `.gitignore` keeps them out
because GitHub doesn't accept files that large.

---

## What to send me next

Paste the full output of step E. We'll read it together and plan the cleaning
in Step 2.

## Words you'll meet in this project

| Word | Plain meaning |
|---|---|
| Portfolio | All the loans a bank holds, looked at as one group |
| Charge-off | The bank gives up on collecting a loan and books it as a loss |
| Default rate | Share of loans that went bad |
| Loss rate | Share of dollars that were lost |
| Vintage | The year a loan was made. Loans from the same year are compared together |
| Concentration | Too much money in one industry, state, or borrower type, so one bad event hurts a lot |
| Limit / tolerance | The maximum share of the portfolio the bank allows in one area |
| NAICS code | A number that tells you a business's industry (e.g. 72 = restaurants and hotels) |
| Credit migration | Loans moving from a healthy status to a worse one (or better) over time |
| Peer benchmarking | Comparing your results with similar banks |
