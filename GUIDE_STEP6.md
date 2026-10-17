# Step 6 Guide: Economic indicators and early warnings

**Why this step matters for the job:** the posting asks you to use "economic
indicators" and "external data sources", to identify "emerging risks", and to
know about "early warning indicators". This step brings in outside economic
data and asks: *could we have seen the 2010 loss peak coming, and how early?*

---

## A. Turn on Python

```powershell
.venv\Scripts\activate
```

## B. Run the early warning questions

```powershell
python scripts/run_sql.py sql/06_early_warnings.sql
```

| Question | What it answers |
|---|---|
| Q1 | How fast did each new vintage fail in its **first 2 years**, compared with normal? When could that be seen? |
| Q2 | Which **industries** got worse first (3-year failure rate, 2001–02 loans vs 2005–06 loans)? |
| Q3 | The same for **states** with 5,000+ loans in each period |

## C. Bring in the unemployment rate and build the signals

```powershell
python scripts/06_economic_indicators.py
```

The script tries to **download** the U.S. unemployment rate from FRED by itself
and saves it as `data\external\UNRATE.csv`.

**If it says it couldn't download**, do it by hand:
1. Open <https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE> in your browser.
   It downloads a small CSV file.
2. Rename the file `UNRATE.csv`.
3. Move it into the folder `data\external\` inside your project.
4. Run the script again.

It saves these in `outputs\`:

| File | What it is |
|---|---|
| `economy_vs_chargeoffs.png` | Chart: unemployment (top) and the portfolio's charge-off rate (bottom) |
| `early_warning_vintages.png` | Chart: the portfolio early warning signal, by the year it could be seen |
| `economic_indicators.csv` | Unemployment, its yearly change, the charge-off rate and the economy signal |
| `early_warning_signals.csv` | Each vintage's early failure rate and its signal |

## D. Save to GitHub

```powershell
git add .
```
```powershell
git commit -m "Step 6: economic indicators and early warnings"
```
```powershell
git push
```

The unemployment file stays off GitHub (everything in `data\` is skipped).
Anyone can download it again from the same link.

---

## What to send me next

Paste the full output of **B** and **C**.

## The two early warning signals

**1. Economy signal: how much did unemployment rise on last year?**

| Rise in unemployment | Signal |
|---|---|
| under 1 percentage point | Green |
| 1 point or more | Amber |
| 2 points or more | Red |

Example: unemployment goes from 5.0% to 6.5%. The rise is 6.5 − 5.0 = 1.5 points, so the signal is **Amber**.

**2. Portfolio signal: how fast are new loans failing compared with normal?**

"Normal" is the average 2-year failure rate of the 2001, 2002 and 2003 vintages.

| Times normal | Signal |
|---|---|
| under 2x | Green |
| 2x or more | Amber |
| 3x or more | Red |

Example: normal is 0.6%, and the newest vintage had 1.5% fail in 2 years.
1.5 ÷ 0.6 = **2.5x**, so the signal is **Amber**.

**Why 2 years?** You only have to wait 2 years after approval to see it.
The final result of a vintage takes about 8 years (Step 3). So this signal
arrives about 6 years earlier than the full answer.

The thresholds are **example settings for this project**. They're at the top of
the script, so you can change them and re-run.

## Correlation, in plain words

Correlation measures how closely two numbers move together, on a scale from −1 to +1.

| Correlation | Meaning |
|---|---|
| +1 | They always rise and fall together |
| 0 | No connection |
| −1 | When one rises, the other falls |

We measure it twice:
- **same year**: unemployment in 2009 against charge-offs in 2009
- **one year apart**: unemployment in 2009 against charge-offs in **2010**

If the second is high, unemployment moves *first*, which makes it useful as a warning.

**Be careful:** we only have about 13 years, and a correlation from so few points
can be strong just by chance. Correlation also doesn't prove that one causes the other.

## New words

| Word | Plain meaning |
|---|---|
| Economic indicator | A number about the whole economy, e.g. unemployment |
| Early warning indicator (EWI) | A number you can see early that warns of trouble later |
| FRED | The Federal Reserve Bank of St. Louis's free economic database |
| Percentage point | The plain difference between two percentages: 5% to 7% is +2 points |
| Correlation | How closely two numbers move together, from −1 to +1 |
| Lag | A delay: one number moves, the other follows later |
| Baseline | The "normal" level you compare against |
