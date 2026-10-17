# Step 5 Guide: How loans move between statuses over time (roll-forward)

**Why this step matters for the job:** the posting asks for analysis of "credit
migration trends" and "credit migration dynamics". Banks track how loans move
from healthy to troubled to lost. This data only has two end statuses (paid off
or charged off), so we track how fast loans move from **performing** to
**charged off**. That's the same idea, using the statuses we have.

**Which loans:** loans approved **2001 onwards**. Charge-off dates before 2001
look incomplete (Step 3).

---

## A. Turn on Python

```powershell
.venv\Scripts\activate
```

## B. Run the roll-forward questions

```powershell
python scripts/run_sql.py sql/05_roll_forward.sql
```

| Question | What it answers |
|---|---|
| Q1 | **Vintage curves**: for each approval year, the % of loans charged off by age 1, 2, 3 ... years |
| Q2 | **Yearly roll-forward**: loans at start + new − charged off − paid off = loans at end |
| Q3 | **Check**: does the roll-forward add up? The `difference` column should be 0 every year |
| Q4 | How **early** in their life did loans fail, before vs during the boom? |

## C. Make the charts

```powershell
python scripts/05_roll_forward_charts.py
```

It saves four files in `outputs\`:

| File | What it is |
|---|---|
| `vintage_curves.png` | Chart: every vintage's curve in grey, with 2002 and 2007 highlighted |
| `annual_chargeoff_rate.png` | Chart: % of outstanding loans charged off each year |
| `vintage_curves.csv` | The curve data (one row per vintage per age) |
| `roll_forward.csv` | The yearly roll-forward table |

## D. Save to GitHub

```powershell
git add .
```
```powershell
git commit -m "Step 5: status roll-forward and vintage curves"
```
```powershell
git push
```

---

## What to send me next

Paste the full output of **B**.

## How to read a vintage curve (Q1)

Each row is one approval year. Each column is a loan age.
A number is the **% of that year's loans charged off by that age**.

Example row: `2007 | age_1 0.3 | age_2 8.7 | age_3 24.2`
- After 1 year, 0.3% of 2007 loans had been charged off.
- After 2 years, 8.7%.
- After 3 years, 24.2%.

**Read down a column to compare vintages fairly.** Every vintage in the
`age_3` column is exactly 3 years old. That fixes the problem from Step 3,
where young vintages looked safe simply because they were young.

## How the roll-forward works (Q2)

It works like a bank statement, but for the number of loans:

```
loans at start of year
+ new loans approved this year
- loans charged off this year
- loans paid off this year
= loans at end of year
```

Example: start 8,000 + new 1,000 − charged off 800 − paid off 300 = **7,900** at the end.

**Annual charge-off rate** = charged off ÷ loans at start of year.
Example: 800 ÷ 8,000 = **10%** of outstanding loans were charged off that year.

**One limit:** the data doesn't say *when* good loans were paid off. We use each
loan's scheduled end date (approval date + term) instead. Loans repaid early
are counted as outstanding for too long. The bottom of the fraction is then too
big, so the rate is a little **too low**. The trend over the years is still valid.

## New words

| Word | Plain meaning |
|---|---|
| Credit migration | Loans moving from one status to another (e.g. healthy to charged off) |
| Vintage curve | A line showing how much of one year's loans went bad as they aged |
| Roll-forward | A start-plus-changes-equals-end table for a portfolio |
| Outstanding | Approved and not yet repaid or charged off |
| Annual charge-off rate | Share of outstanding loans charged off during the year |
| Tie out | Check that the numbers add up exactly |
