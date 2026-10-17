# Step 7 Guide: Peer benchmarking (comparing like with like)

**Why this step matters for the job:** the posting asks for "peer benchmarking"
and "portfolio performance measurement". The skill being tested is comparing
lenders (or states, or teams) **fairly**, not just ranking raw numbers.

**Which loans:** approved **2001–2010**, the same as Step 4.

---

## A. Turn on Python

```powershell
.venv\Scripts\activate
```

## B. Run the benchmarking questions

```powershell
python scripts/run_sql.py sql/07_peer_benchmarking.sql
```

| Question | What it answers |
|---|---|
| Q1 | The 15 largest lenders, plus **KeyBank**: raw comparison vs fair comparison |
| Q2 | **KeyBank close up**: actual vs expected for each loan size |
| Q3 | The 15 largest **states**, compared fairly (revisits Step 4) |

## C. Make the tables and chart

```powershell
python scripts/07_peer_benchmarking.py
```

It saves these in `outputs\`:

| File | What it is |
|---|---|
| `lender_benchmark.png` | Chart: each large lender's raw index (grey) and fair index (blue) |
| `lender_benchmark.csv` | Every lender with 300+ loans, fairly compared. Open it in Excel |
| `state_benchmark.csv` | Every state, fairly compared |

## D. Save to GitHub

```powershell
git add .
```
```powershell
git commit -m "Step 7: peer benchmarking"
```
```powershell
git push
```

---

## What to send me next

Paste the full output of **B**.

## Why raw comparisons are unfair

Two things we already found change a lender's results, whatever its skill:
- **Loan size:** loans under $50K fail about 3 times as often as $1M+ loans (Step 4)
- **Year:** 2007 loans failed about 10 times as fast as 2002 loans (Step 5)

A lender making small loans in 2007 will look bad even if it lends carefully.
It's like comparing two students' scores when one sat a much harder exam.

## The fair method: actual vs expected

1. Put every loan in a **box**: approval year × loan size × industry.
2. Work out the default rate of **all lenders together** in each box: the **peer rate**.
3. For each lender, add up the peer rates of its own loans: its **expected** defaults.
4. **Performance index = actual defaults ÷ expected defaults.**

**Worked example.** A lender made 100 loans:
- 50 small 2007 restaurant loans, where peers had a 40% default rate, so 50 × 0.40 = **20** expected
- 50 large 2002 manufacturing loans, where peers had a 4% default rate, so 50 × 0.04 = **2** expected
- Expected in total: 20 + 2 = **22** defaults

If the lender actually had **18** defaults, its index is 18 ÷ 22 = **0.82**:
18% fewer defaults than peers on the same kind of loans. That's **better** than
peers, even though its raw default rate (18%) might look high.

| Index | Meaning |
|---|---|
| 1.00 | Exactly like peers |
| above 1 | More defaults than peers on the same kind of loans (worse) |
| below 1 | Fewer defaults than peers (better) |

**Loss index** is the same idea using dollars lost instead of the number of defaults.

## Is the difference real or just luck?

A small lender can be above 1 by chance. The rule of thumb we use:
the difference is **clear** when

  |actual − expected| > 2 × √expected

Example: expected 400 defaults. √400 = 20, and 2 × 20 = 40.
- Actual 460: the gap is 60. 60 > 40, so this is clearly **worse than peers**.
- Actual 420: the gap is 20. 20 < 40, so it is **in line with peers** (could be luck).

## New words

| Word | Plain meaning |
|---|---|
| Peer benchmarking | Comparing your results with similar lenders |
| Mix | What kind of loans a lender holds (sizes, years, industries) |
| Mix-adjusted / like-for-like | Compared after taking the mix into account |
| Expected defaults | Defaults the lender would have had if it did exactly as well as peers |
| Performance index | Actual ÷ expected. Above 1 is worse, below 1 is better |
| Statistically clear | Too big a difference to be explained by luck alone |
