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
