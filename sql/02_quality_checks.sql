-- ============================================================================
-- STEP 2a: DATA QUALITY CHECKS
-- Run with:  python scripts/run_sql.py sql/02_quality_checks.sql
--
-- These queries only LOOK at the data. Nothing is changed or deleted.
-- An analyst always checks the data before trusting any result built on it.
-- After this, scripts/02_clean_data.py does the actual cleaning.
-- ============================================================================


-- Q1. How many values are missing in each important column?
-- COUNT(*) counts every row. COUNT(column) counts only rows where that column
-- has a value. So COUNT(*) - COUNT(column) = number of missing values.
SELECT
    COUNT(*)                            AS total_loans,
    COUNT(*) - COUNT(loan_status)       AS missing_status,
    COUNT(*) - COUNT(naics_code)        AS missing_industry,
    COUNT(*) - COUNT(state)             AS missing_state,
    COUNT(*) - COUNT(lender)            AS missing_lender,
    COUNT(*) - COUNT(loan_amount)       AS missing_amount,
    COUNT(*) - COUNT(approval_date)     AS missing_approval_date,
    COUNT(*) - COUNT(term_months)       AS missing_term
FROM loans;


-- Q2. Testing our guess: is the missing industry mostly on OLD loans?
-- The NAICS industry codes were introduced in 1997, so we expect older loans
-- to be missing them. If the guess is right, the percent missing should drop
-- sharply around 1997-1998.
SELECT
    approval_year,
    COUNT(*)                                                          AS number_of_loans,
    COUNT(*) - COUNT(naics_code)                                      AS missing_industry,
    ROUND(100.0 * (COUNT(*) - COUNT(naics_code)) / COUNT(*), 1)       AS percent_missing
FROM loans
WHERE approval_year >= 1985
GROUP BY approval_year
ORDER BY approval_year;


-- Q3. Which years do the loans with NO status come from?
-- If they are spread evenly, they are random gaps. If they bunch in one
-- period, something specific happened to those records.
SELECT
    approval_year,
    COUNT(*)  AS loans_with_no_status
FROM loans
WHERE loan_status IS NULL
GROUP BY approval_year
ORDER BY loans_with_no_status DESC
LIMIT 10;


-- Q4. Values that look wrong or don't make sense together
-- Each row of the answer is one check. UNION ALL stacks the answers on top
-- of each other so we get one neat list.
SELECT 'Loan amount is zero or negative'              AS check_name, COUNT(*) AS number_of_loans
FROM loans WHERE loan_amount <= 0
UNION ALL
SELECT 'Loan term is 0 months',                        COUNT(*)
FROM loans WHERE term_months = 0
UNION ALL
SELECT 'Charged off, but loss recorded as $0',        COUNT(*)
FROM loans WHERE loan_status = 'CHGOFF' AND charge_off_amount = 0
UNION ALL
SELECT 'Paid in full, but a loss is recorded',         COUNT(*)
FROM loans WHERE loan_status = 'PIF' AND charge_off_amount > 0
UNION ALL
SELECT 'Loss is bigger than the loan amount',          COUNT(*)
FROM loans WHERE charge_off_amount > loan_amount;


-- Q5. Date problems
-- The raw file writes years with only 2 digits, like 28-Feb-62. The computer has
-- to guess the century, and it reads "62" as 2062, not 1962. We catch this by
-- comparing the date's year with the approval year column. (They can differ by 1,
-- because the government's fiscal year starts on October 1.)
SELECT 'Approval date is in the wrong century'          AS check_name, COUNT(*) AS number_of_loans
FROM loans WHERE ABS(YEAR(approval_date) - approval_year) > 1
UNION ALL
SELECT 'Charge-off date is before the approval date',   COUNT(*)
FROM loans WHERE charge_off_date < approval_date;


-- Q6. Are any loans in the file twice?
-- We check the ORIGINAL table (loans_raw), which still has every column,
-- including the borrower's name and address. Two rows that are identical in
-- every single column are a true duplicate, not two similar loans.
SELECT
    CAST(COALESCE(SUM(copies - 1), 0) AS INTEGER)    AS extra_duplicate_rows
FROM (
    SELECT *, COUNT(*) AS copies
    FROM (SELECT * EXCLUDE (filename) FROM loans_raw)
    GROUP BY ALL
    HAVING COUNT(*) > 1
);


-- Q7. State values that are not a normal 2-letter code
-- LENGTH(state) <> 2 means "the text is not exactly 2 characters long".
SELECT
    COALESCE(state, '(missing)')   AS state_value,
    COUNT(*)                       AS number_of_loans
FROM loans
WHERE state IS NULL OR LENGTH(TRIM(state)) <> 2
GROUP BY state
ORDER BY number_of_loans DESC;


-- Q8. Are the most recent years complete?
-- The data was collected in 2014. A loan approved in 2013 has only had about a
-- year to either be paid off or go bad. We look at the default rate by year to
-- see whether recent years behave very differently from earlier ones.
SELECT
    approval_year,
    COUNT(*)                                                                AS number_of_loans,
    ROUND(100.0 * COUNT(*) FILTER (WHERE loan_status = 'CHGOFF') / COUNT(*), 1)
                                                                            AS percent_charged_off
FROM loans
WHERE approval_year >= 2000
GROUP BY approval_year
ORDER BY approval_year;
