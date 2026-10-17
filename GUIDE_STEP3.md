# Step 3 Guide: Vintage analysis (portfolio performance by approval year)

**Why this step matters for the job:** the posting asks for "portfolio performance
measurement" and analysis of "emerging risks" and "credit migration trends".
Vintage analysis is the standard way credit teams answer *"are the loans we made
in a given year behaving worse than usual, and why?"*

---

## A. Install the chart tool (one time)

We now draw charts with a Python library called **matplotlib**.

```powershell
.venv\Scripts\activate
```
```powershell
pip install -r requirements.txt
```

## B. Run the vintage questions

```powershell
python scripts/run_sql.py sql/03_vintage_analysis.sql
```

| Question | What it answers |
|---|---|
| Q1 | How long after approval do loans usually go bad? This decides which years are "too young to judge" |
| Q2 | The vintage table: default rate, loss rate and loss severity for each approval year |
| Q3 | The same, grouped into 5 eras, the version you'd show leadership |
| Q4 | **When** the losses actually arrived (by the year each loan was charged off) |
| Q5 | Whether the odd loans we flagged in Step 2 change the results |

## C. Make the charts

```powershell
python scripts/03_vintage_charts.py
```

This saves four files in `outputs\`:

| File | What it is |
|---|---|
| `vintage_performance.png` | Chart: default rate and loss rate for each approval year |
| `losses_by_year.png` | Chart: dollars lost in each calendar year |
| `vintage_performance.csv` | The vintage table, ready for Excel or Power BI |
| `losses_by_year.csv` | The losses table |

Open the two PNG files and look at them before sending me the output.

## D. Save to GitHub

```powershell
git add .
```
```powershell
git status
```
Check the list shows only code, guides and `outputs` files (no `data` or `.venv`), then:
```powershell
git commit -m "Step 3: vintage analysis"
```
```powershell
git push
```

---

## What to send me next

Paste the full output of **B**. I'll add the findings and the charts to your README.

## The three measures, in plain words

| Measure | Question it answers | How it's calculated |
|---|---|---|
| **Default rate** | How *often* did loans go bad? | loans charged off ÷ all loans |
| **Loss rate** | How many *dollars* were lost? | dollars charged off ÷ dollars approved |
| **Loss severity** | When a loan went bad, how *bad* was it? | dollars charged off ÷ dollars approved, bad loans only |

They fit together: **loss rate ≈ default rate × loss severity.**
Example: if 20% of loans go bad and each loses 40% of its amount,
then about 0.20 × 0.40 = 0.08, so **8%** of all dollars are lost.

## New words

| Word | Plain meaning |
|---|---|
| Vintage | All the loans approved in the same year |
| Seasoned | Old enough that most of its defaults have already happened |
| Cumulative percent | A running total, e.g. "72% of defaults happened in the first 3 years" |
| Loss severity | Also called *loss given default (LGD)* in banking |
| Charge-off year | The year the bank officially gave up on the loan and booked the loss |
