# Step 8 Guide: Excel limits workbook and Power BI dashboard

**Why this step matters for the job:** the posting asks for "advanced proficiency
with Microsoft Excel", experience "developing data visualizations, dashboards,
and analytical reporting using Tableau, Power BI, or similar tools", and the
"annual recalibration of portfolio tolerances, limits". This step delivers all three.

Allow about **2–3 hours** for the Power BI part the first time. Take it one page at a time.

---

## Part A: The Excel limits workbook (about 5 minutes)

### A1. Install the Excel library (one time)

```powershell
.venv\Scripts\activate
```
```powershell
pip install -r requirements.txt
```

### A2. Build the workbook

```powershell
python scripts/08_build_limits_workbook.py
```

### A3. Open it and try it

Open `outputs\concentration_limits.xlsx` in Excel.

| Sheet | What's on it |
|---|---|
| **Read Me** | What the workbook is and how to use it |
| **Summary** | Counts of Breach / Watch / Within, largest exposures, and a check that shares add to 100% |
| **Settings** | The limit settings, in **yellow** cells you can change |
| **Limit Monitor** | One row per industry and state. Limit, headroom, % used and status are **formulas** |

**Try this:** on **Settings**, change the **Industry limit** (cell B4) from 15% to 18%.
Go to **Summary**: the number of industry breaches changes by itself.
Put it back to 15% afterwards.

That's a "limit recalibration": change the policy and see its effect at once.
It also makes a good interview demo.

**Formulas used** (worth being able to explain):

| Column | Formula idea |
|---|---|
| Risk index | `= share of losses / share of dollars` |
| High risk? | `=IF(risk index > Settings!B8, "Yes", "No")` |
| Limit | `=IF(Industry, IF(high risk, B5, B4), IF(high risk, B7, B6))` |
| Headroom | `= limit − share of dollars` |
| Limit used | `= share of dollars / limit` |
| Status | `=IF(used > 1, "Breach", IF(used >= watch level, "Watch", "Within"))` |
| Summary counts | `COUNTIFS` (count rows that match two conditions) |
| Largest exposure | `INDEX` / `MATCH` (look up the name next to the biggest value) |

---

## Part B: Get the data ready for Power BI (about 2 minutes)

Make sure you have run Steps 3–7 (so their tables exist), then:

```powershell
python scripts/08_export_dashboard_data.py
```

It should print **OK** four times (the totals check) and copy 8 tables.
Everything Power BI needs is now in `outputs\dashboard\`.

---

## Part C: Build the Power BI dashboard

### C1. Install Power BI Desktop (free, one time)

Open the **Microsoft Store** app on Windows, search **Power BI Desktop**, and click **Get**.
When it opens, you can close any sign-in box: you don't need an account for this.

### C2. Load the data

1. **Home → Get data → Text/CSV**.
2. Go to your project's `outputs\dashboard` folder, pick **portfolio_cube.csv**, click **Open**, then **Load**.
3. Repeat for these five files, one at a time:
   `limit_monitor.csv`, `vintage_curves.csv`, `early_warning_signals.csv`,
   `economic_indicators.csv`, `lender_benchmark.csv`

You'll see all six tables in the **Data** pane on the right.

### C3. Create the measures (the formulas Power BI calculates)

A **measure** is a formula that recalculates for whatever you've filtered,
like a SUMIFS that updates itself.

For each line below: in the **Data** pane, right-click **portfolio_cube** →
**New measure**, paste the line into the formula bar at the top, and press **Enter**.

```
Loans = SUM(portfolio_cube[number_of_loans])
```
```
Approved Dollars = SUM(portfolio_cube[approved_dollars])
```
```
Defaults = SUM(portfolio_cube[loans_charged_off])
```
```
Dollars Lost = SUM(portfolio_cube[dollars_charged_off])
```
```
Default Rate = DIVIDE([Defaults], [Loans])
```
```
Loss Rate = DIVIDE([Dollars Lost], [Approved Dollars])
```
```
Share of Dollars = DIVIDE([Approved Dollars], CALCULATE([Approved Dollars], ALLSELECTED(portfolio_cube)))
```

**Show the rates as percentages:** click **Default Rate** in the Data pane. In the
**Measure tools** ribbon at the top, set **Format** to **Percentage** with 1 decimal place.
Do the same for **Loss Rate** and **Share of Dollars**.

What the last one does: `ALLSELECTED` means "the total of everything currently
selected", so Share of Dollars = this group's dollars ÷ all selected dollars.

### C4. Page 1: Portfolio Overview

Rename the page: double-click **Page 1** at the bottom and type `Portfolio Overview`.

1. **Four headline cards.** In **Visualizations**, click **Card**, then tick **Loans** in the Data pane.
   Make three more cards for **Approved Dollars**, **Default Rate** and **Loss Rate**.
   Line them up across the top.
2. **Default rate by year.** Click **Clustered column chart**. Drag **approval_year**
   to **X-axis** and **Default Rate** to **Y-axis**.
   (If approval_year turns into "Sum of approval_year", click its arrow in the X-axis box and choose **Don't summarize**.)
3. **Filters people can click (slicers).** Click **Slicer** and drag **era** into it.
   Make three more slicers for **industry**, **state** and **loan_size_band**.

Try it: click **2005-2008** in the era slicer. All the cards and the chart change.

### C5. Page 2: Concentrations & Limits

Click **+** at the bottom for a new page and name it `Concentrations & Limits`.

1. **Limit monitor table.** Click **Table**, then tick from **limit_monitor**:
   dimension, group_name, pct_of_dollars, risk_index, limit_pct, headroom_pct, limit_used, status.
2. **Colour the limit used column.** In the **Columns** box, click the arrow next to
   **limit_used** → **Conditional formatting** → **Background color**.
   Set **Format style** to **Rules** and add three rules:
   - if value **>** 1, then light red
   - if value **>=** 0.8 and **<=** 1, then light amber
   - if value **<** 0.8, then light green
3. **Industry share chart.** Click **Clustered bar chart**. From **portfolio_cube**, drag
   **industry** to **Y-axis** and **Share of Dollars** to **X-axis**.
   In the **Filters** pane, drag **approval_year** onto "Filters on this visual",
   choose **Advanced filtering**: *is greater than or equal to* 2001 **And** *is less than or equal to* 2010.

### C6. Page 3: Early Warnings

New page, name it `Early Warnings`.

1. **Early warning signal.** Click **Clustered column chart**. From **early_warning_signals**,
   **year_known** to X-axis (Don't summarize) and **times_baseline** to Y-axis.
   Colour it: **Format visual** (paintbrush) → **Columns** → **Colors** → the **fx** button →
   **Format style: Rules**: ≥ 3 red, ≥ 2 and < 3 amber, < 2 green.
2. **Vintage curves.** Click **Line chart**. From **vintage_curves**,
   **loan_age_years** to X-axis (Don't summarize), **cumulative_chargeoff_pct** to Y-axis,
   **vintage** to Legend. In the Filters pane, keep only vintages **2002, 2005, 2007, 2009**
   (too many lines are hard to read).
3. **Unemployment.** Click **Line chart**. From **economic_indicators**,
   **year** to X-axis (Don't summarize) and **unemployment_rate** to Y-axis.

### C7. Page 4: Peer Benchmarking

New page, name it `Peer Benchmarking`.

1. **Benchmark table.** Click **Table**, then tick from **lender_benchmark**:
   group_name, number_of_loans, raw_index, performance_index, loss_index, verdict.
   In the Filters pane, set **dashboard_group** to **Top 15** and **KeyBank** only.
2. **Colour the performance index.** Conditional formatting on **performance_index**,
   Background color, Rules: > 1 light red, < 1 light green.
3. **Bar chart.** Click **Clustered bar chart**: **group_name** to Y-axis,
   **performance_index** to X-axis, with the same dashboard_group filter.

### C8. Finishing touches

- Add a **Text box** (Insert → Text box) at the top of each page with a one-line title,
  e.g. *"SBA 7(a) loan portfolio, 1989–2014: 882,533 loans"*.
- Use the same order on each page: title, then cards or the main chart, then details.
- Don't add colours just for decoration. Keep red/amber/green for status only.

### C9. Save and export

1. **File → Save as**, name it `credit_portfolio_dashboard`, and save it in `outputs\dashboard\`.
2. **File → Export → Export to PDF**. Save as `outputs\dashboard\dashboard.pdf`.
3. Screenshot the Portfolio Overview page: press **Windows + Shift + S**, drag over the page,
   then open **Snipping Tool** from the notification and save it as
   `outputs\dashboard\overview.png`. Do the same for the other pages:
   `limits.png`, `early_warnings.png`, `benchmarking.png`.

The README already shows these four pictures, so they'll appear on GitHub
once the files exist with exactly these names.

---

## Part D: Save to GitHub

```powershell
git add .
```
```powershell
git status
```
You should see the workbook, the dashboard file (`.pbix`), the PDF, the PNGs and the CSVs.
No `data` or `.venv` files. Then:
```powershell
git commit -m "Step 8: Excel limits workbook and Power BI dashboard"
```
```powershell
git push
```

---

## If something goes wrong in Power BI

| Problem | Fix |
|---|---|
| A year shows as "Sum of approval_year" | Click the arrow next to it in the field box → **Don't summarize** |
| Numbers look like 0.25 instead of 25% | Click the measure → **Measure tools** → Format → **Percentage** |
| A chart is empty after filtering | Check the **Filters** pane for a filter you forgot |
| Charts on one page react oddly to another table's slicer | **Modeling → Manage relationships** and delete any relationships Power BI created by itself |

Send me a screenshot whenever you're stuck.

## New words

| Word | Plain meaning |
|---|---|
| Dashboard | One screen of charts and numbers that update together |
| Measure (DAX) | A Power BI formula that recalculates for the current filters |
| Slicer | A clickable filter on the page |
| Cube | A summary table you can slice any way and still have totals add up |
| Conditional formatting | Colouring cells by rules, e.g. red when over the limit |
| COUNTIFS | Excel: count rows that meet several conditions |
| INDEX / MATCH | Excel: find a value, then return the item next to it |
