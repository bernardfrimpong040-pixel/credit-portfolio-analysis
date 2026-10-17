# Commercial Credit Portfolio Analysis (SBA 7(a) Loans)

**Author:** Bernard Frimpong
**Tools:** Python, SQL (DuckDB), Excel, Power BI / Tableau Public

## The question this project answers

> If I managed a commercial loan portfolio, where are the risks concentrated,
> how is the portfolio performing over time, and what should senior leaders watch?

I act as a **credit portfolio analyst** looking after a real portfolio of
U.S. small-business loans. These loans were made by banks and guaranteed by the
U.S. Small Business Administration (SBA). The data is free, public, and covers
about 900,000 real loans with their industry, state, lender, size,
and final outcome (paid back in full or charged off as a loss), including
the 2008 financial crisis.

## Data sources

| Source | What it gives us | Link |
|---|---|---|
| SBA national loan data (Kaggle) | ~900,000 SBA loans approved up to 2014: amount, industry (NAICS), state, lender, status, charge-off amount | https://www.kaggle.com/datasets/mirbektoktogaraev/should-this-loan-be-approved-or-denied |
| FRED (Federal Reserve Bank of St. Louis) | Economic indicators, e.g. unemployment rate | https://fred.stlouisfed.org/ |

## Roadmap (one step at a time)

Each step matches something the job postings ask for.

| Step | What we build | Job skill it proves |
|---|---|---|
| 1 | Load the loan data into a SQL database and take a first look | SQL, Python, working with large datasets |
| 2 | Data quality checks and cleaning | Attention to detail, data quality |
| 3 | Portfolio performance: default rates and loss rates by approval year ("vintage") | Portfolio performance measurement |
| 4 | Risk concentrations: by industry, state, and loan size, with limits | Concentration management, tolerances and limits |
| 5 | Status roll-forward: how each yearly group of loans moves from active to paid off or charged off over time | Credit migration–style analysis |
| 6 | Economic indicators and early warnings: unemployment vs. charge-offs, rising-risk industries | Economic indicators, early warning indicators, emerging risks |
| 7 | Peer benchmarking: compare lenders' loss rates against the whole portfolio | Peer benchmarking |
| 8 | Dashboard in Power BI or Tableau Public, plus an Excel limits workbook | Dashboards, Excel |
| 9 | 5-slide executive summary with recommendations | Presenting to senior leadership, PowerPoint |

## How to run it

See `GUIDE_STEP1.md` for setup and the first step.

## Project layout

```
credit-portfolio-analysis/
├── data/
│   ├── raw/          <- the SBA CSV files you download go here (not uploaded to GitHub)
│   └── loans.duckdb  <- the database our scripts build (not uploaded to GitHub)
├── scripts/          <- Python scripts, run in number order
├── sql/              <- SQL query files
├── outputs/          <- charts and tables we produce
└── README.md
```

## Findings

### Step 2: Data quality

Starting data: **899,164 loans** (FY1962–FY2014), $173.3B approved.

| Rule | Reason | Loans removed | Loans left |
|---|---|---:|---:|
| 1 | Approved before 1989 (too few loans to measure reliably) | 14,715 | 884,449 |
| 2 | No final status (can't tell if repaid or lost) | 1,916 | 882,533 |
| 3 | Loan amount missing, zero or negative | 0 | 882,533 |

**Kept 882,533 loans (98.2%), $170.2B approved, 17.07% charged off.**
Full log: [`outputs/data_quality_log.csv`](outputs/data_quality_log.csv)

What the checks found:
- **No duplicate loans**, and fewer than 0.2% of loans are missing a state or lender.
- **Industry codes are missing for about 55% of loans approved before 2001**, and almost none after. Industry analysis therefore uses loans from 2001 onwards.
- **Dates with 2-digit years** ("62") were read as 2062. These were all 1960s loans, removed by rule 1. 0 date problems remain after cleaning.
- **Odd but kept (flagged) loans:** 4,698 paid in full with a loss recorded, 792 with a 0-month term, 531 with a loss bigger than the approved amount, 236 charged off with a $0 loss. Together they are under 0.7% of loans; later steps check that they don't change the results.
- **Recent loans are too young to judge.** Loans approved 2011–2014 show charge-off rates of 1.9%–7.8%, because most had only 1–3 years to fail before the data was collected in 2014. They are labelled as unseasoned in the analysis rather than treated as safe.
- **First signal of risk timing:** loans approved in 2007 charged off at 42.7%, 3.7 times the 11.4% rate for 2000 loans. Step 3 investigates this.

### Step 3: Vintage analysis (performance by approval year)

![Default rate and loss rate by approval year](outputs/vintage_performance.png)

**Headline: loans approved in 2005–2008 were 21% of the dollars lent but caused 54% of all losses.**

| Era (approval years) | Loans | Approved | Default rate | Loss rate | Dollars lost |
|---|---:|---:|---:|---:|---:|
| 1989–1999 | 316,302 | $70.7B | 4.9% | 2.6% | $1.84B |
| 2000–2004 (before the boom) | 245,171 | $50.3B | 14.1% | 6.0% | $3.00B |
| **2005–2008 (boom, then crisis)** | **263,821** | **$36.2B** | **35.2%** | **16.9%** | **$6.11B** |
| 2009–2010 (after the crisis) | 35,931 | $6.9B | 17.5% | 5.6% | $0.38B |
| 2011–2014 (too young to judge) | 21,308 | $6.0B | 6.6% | 1.5% | $0.09B |

Full table by year: [`outputs/vintage_performance.csv`](outputs/vintage_performance.csv)

Findings:
1. **Loans need about 8 years before they can be judged.** Among 1989–2005 loans, only 32.5% of charge-offs happened within 4 years of approval, 49.1% within 5 years, and 87.0% within 8 years. Vintages are therefore labelled *seasoned* (8+ years old in 2014), *partly seasoned* (4–7 years: rates are minimums and can still rise) or *too young to judge* (under 4 years).
2. **The worst vintages were made at the top of the boom.** 2007 loans defaulted at 42.8% and lost 22.8% of approved dollars, against 1.9% and 0.8% for 1993 loans. Because 2007–2008 are only partly seasoned, their true rates are likely even higher.
3. **Bad loans also got worse.** Loss severity (share of a defaulted loan's amount that was lost) rose from 42–44% for 1992–1994 vintages to 78% for 2007–2008, consistent with falling collateral values in the crisis.
4. **Defaulted loans were smaller than average.** For 2007, 42.8% of *loans* defaulted, but those loans held only about 29% of the *dollars* (loss rate 22.8% ÷ severity 77.6%). Smaller loans default more often, which Step 4 tests directly.
5. **Losses arrived about 5 years after the lending peak.** Lending peaked in 2005 (76,958 loans); dollars charged off peaked in 2010 ($2.06B). 2008–2011 together account for $5.94B, about half of all recorded charge-offs.

![Dollars charged off per year](outputs/losses_by_year.png)

Checks and limitations:
- **Flagged loans don't change the result:** removing all 6,215 flagged loans moves the default rate from 17.07% to 17.02% and the loss rate from 6.71% to 6.59%.
- **Charge-off dates before 2001 look incomplete.** Only 3,587 charge-offs are dated 1989–2000, although 1990s vintages alone have about 15,500 defaults. Default *rates* (based on loan status) are unaffected; *timing* results (findings 1 and 5) lean on post-2001 records.
