# Step 4 Guide: Risk concentrations and limits

**Why this step matters for the job:** the posting asks you to analyse "risk
concentrations", support "concentration management", and carry out the "annual
recalibration of portfolio tolerances, limits, and related monitoring
frameworks". This step builds a small version of exactly that.

**Which loans:** loans approved **2001–2010**. Industry codes are recorded from
2001 (Step 2), and these loans are at least 4 years old (Step 3).

---

## A. Turn on Python

```powershell
.venv\Scripts\activate
```

## B. Run the concentration questions

```powershell
python scripts/run_sql.py sql/04_concentrations.sql
```

| Question | What it answers |
|---|---|
| Q1 | How much money is in each **industry**, and does it lose more than its size suggests? |
| Q2 | The same for the 15 biggest **states** |
| Q3 | Do **small loans** go bad more often than big ones? |
| Q4 | Which **lenders** hold the most money, and how risky are their loans? |
| Q5 | One number for how concentrated each of these is: the **HHI** |

## C. Run the limit monitor and charts

```powershell
python scripts/04_concentration_limits.py
```

It saves three files in `outputs\`:

| File | What it is |
|---|---|
| `limit_monitor.csv` | Every industry and state with its share, limit and status. Open it in Excel |
| `industry_concentration.png` | Chart: each industry's share of money lent vs share of money lost |
| `loan_size_risk.png` | Chart: default rate for each loan size |

## D. Save to GitHub

```powershell
git add .
```
```powershell
git status
```
Check there are no `data` or `.venv` files in the list, then:
```powershell
git commit -m "Step 4: risk concentrations and limits"
```
```powershell
git push
```

---

## What to send me next

Paste the full output of **B** and **C**.

## How the limits work

The limits are **example settings for this project**, not real SBA or bank
policy. They live at the top of `scripts/04_concentration_limits.py`, so you
can change them and re-run.

| Setting | Value | Meaning |
|---|---|---|
| Industry limit | 15% | No industry should hold more than 15% of the money |
| Industry limit, high risk | 10% | Tighter, for industries with a risk index above 1.25 |
| State limit | 10% | No state should hold more than 10% of the money |
| State limit, high risk | 7.5% | Tighter, for states with a risk index above 1.25 |
| Watch level | 80% | "Watch" once a group has used 80% of its limit |

**Status:**
- **Breach**: share is above the limit
- **Watch**: share is at 80% or more of the limit
- **Within**: comfortably inside the limit

**Worked example.** Say restaurants hold 12% of the money and their risk index
is 1.5. Because 1.5 is above 1.25, they get the tighter 10% limit.
12% is above 10%, so the status is **Breach**, with headroom 10 − 12 = **−2%**.

## The risk index, in plain words

risk index = share of money **lost** ÷ share of money **lent**

| Risk index | Meaning |
|---|---|
| 1.0 | Loses money at the same rate as the whole portfolio |
| 2.0 | Loses twice as much as its size suggests |
| 0.5 | Loses half as much |

Example: an industry got 10% of the money but caused 15% of the losses.
Risk index = 15 ÷ 10 = **1.5**.

## The HHI, in plain words

Square each group's share (in %) and add them up.

- 4 groups with 25% each: 25² × 4 = 625 × 4 = **2,500**
- 100 groups with 1% each: 1² × 100 = **100**

The bigger the number, the more the money is bunched up. US competition
regulators call 1,000–1,800 *moderately concentrated* and above 1,800 *highly
concentrated* (2023 Merger Guidelines). We borrow that scale.

**Equivalent groups** = 10,000 ÷ HHI. For example, an HHI of 2,500 gives
10,000 ÷ 2,500 = 4, so the portfolio is "as spread out as 4 equal groups".

## New words

| Word | Plain meaning |
|---|---|
| Concentration | A lot of money in one industry, state, lender or loan type |
| Exposure | How much money the bank has at risk in a group |
| Limit / tolerance | The most of the portfolio a group is allowed to hold |
| Headroom | How much room is left before the limit (negative = over the limit) |
| Breach | The limit has been broken |
| Risk-adjusted limit | A smaller limit for riskier groups |
