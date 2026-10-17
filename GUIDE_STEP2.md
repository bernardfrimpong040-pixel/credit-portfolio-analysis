# Step 2 Guide: Check the data quality, then clean it

**Why this step matters for the job:** the posting asks for "attention to detail"
and "data quality". In a bank, any number you show leadership has to survive the
question *"how do you know the data is right?"* This step is your answer.

---

## A. Open the project and turn on Python

In VS Code, open the `credit-portfolio-analysis` folder, open a terminal, and run:

```powershell
.venv\Scripts\activate
```

## B. Run the quality checks (they only look, nothing is changed)

```powershell
python scripts/run_sql.py sql/02_quality_checks.sql
```

Before you run it, open `sql/02_quality_checks.sql` and read the comment above
each question. Guess the answer first, then compare.

| Question | What it checks |
|---|---|
| Q1 | How many values are missing in each important column |
| Q2 | Whether missing industry codes are mostly old loans (from before NAICS existed in 1997) |
| Q3 | Which years the loans with no status come from |
| Q4 | Values that don't make sense, e.g. a charged-off loan with $0 loss |
| Q5 | Dates read in the wrong century (2-digit years like "62") |
| Q6 | Loans that appear in the file twice |
| Q7 | State codes that aren't normal 2-letter codes |
| Q8 | Whether the most recent years look different from earlier ones |

## C. Run the cleaning script

```powershell
python scripts/02_clean_data.py
```

It creates a new table `loans_clean` and leaves the original `loans` table alone.
It removes rows using three rules, and prints how many each rule removed:

1. **Approved before 1989.** Too few loans to measure reliably.
2. **No final status, or cancelled.** We can't tell if the loan was repaid or lost.
3. **Loan amount missing, zero or negative.** A loan of $0 isn't a real loan.

It also adds columns we'll use later:

| New column | Meaning |
|---|---|
| `is_default` | 1 if the loan was charged off, 0 if not. Its average *is* the default rate |
| `sector_name` | Readable industry name, or "Not recorded" |
| `loan_size_band` | Loan size group: under $50K, $50K–$150K, $150K–$350K, $350K–$1M, $1M+ |
| `flag_chgoff_no_loss` | TRUE if the loan was charged off but the loss is recorded as $0 |
| `flag_loss_over_amount` | TRUE if the recorded loss is bigger than the loan |

The flagged rows are **kept but marked**, so later we can check whether they
change any result. Deleting things you don't understand is a common beginner
mistake; marking them is safer.

The list of removed rows is saved to `outputs/data_quality_log.csv`.
Open it in Excel. This small file goes on GitHub as proof of your cleaning.

## D. Save to GitHub

In GitHub Desktop: **Changes** tab → you'll see the new files →
summary `Step 2: data quality checks and cleaning` → **Commit to main** → **Push origin**.

---

## What to send me next

Paste the full output of **both** B and C. We'll read them together and write up
the data quality findings for your README.

## New words

| Word | Plain meaning |
|---|---|
| Data quality check | A query that looks for missing, impossible or suspicious values |
| Audit trail | A record of every change made to the data and why |
| Flag | A TRUE/FALSE marker on a row that looks odd, kept instead of deleted |
| Fiscal year | The government's year, which starts on October 1 |
| Seasoning | How long a loan has existed. Young loans haven't had time to show their outcome |
