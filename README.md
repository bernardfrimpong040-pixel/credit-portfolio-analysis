# Commercial Credit Portfolio Analysis (SBA 7(a) Loans)

**Author:** Bernard Frimpong
**Tools:** Python, SQL (DuckDB), Excel, Power BI / Tableau Public

## The question this project answers

> If I managed a commercial loan portfolio, where are the risks concentrated,
> how is the portfolio performing over time, and what should senior leaders watch?

I act as a **credit portfolio analyst** looking after a real portfolio of
U.S. small-business loans. These loans were made by banks and guaranteed by the
U.S. Small Business Administration (SBA). The data is free, public, and covers
hundreds of thousands of real loans with their industry, state, lender, size,
and final outcome (paid back in full or charged off as a loss).

## Data sources

| Source | What it gives us | Link |
|---|---|---|
| SBA 7(a) FOIA loan data | Every 7(a) loan: amount, industry (NAICS), state, lender, status, charge-off amount | https://data.sba.gov/dataset/7-a-504-foia |
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

*(Filled in as the project progresses.)*
