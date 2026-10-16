-- ============================================================================
-- STEP 1: FIRST LOOK AT THE LOAN PORTFOLIO
-- Run with:  python scripts/run_sql.py sql/01_first_look.sql
--
-- Every query below answers one simple question. Read the comment, guess the
-- answer, then run the file and compare. That habit is how analysts think.
-- ============================================================================


-- Q1. How big is the portfolio? (number of loans, years covered, total dollars)
SELECT
    COUNT(*)                            AS number_of_loans,
    MIN(approval_year)                  AS first_year,
    MAX(approval_year)                  AS last_year,
    ROUND(SUM(loan_amount) / 1e9, 2)    AS total_approved_billions,
    ROUND(AVG(loan_amount), 0)          AS average_loan_size
FROM loans;


-- Q2. What happened to the loans? (count of each loan status)
-- PIF = paid in full, CHGOFF = charged off (a loss), EXEMPT / COMMIT = still active,
-- CANCLD = cancelled before the money was given out
SELECT
    loan_status,
    COUNT(*)                                                AS number_of_loans,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)      AS percent_of_loans
FROM loans
GROUP BY loan_status
ORDER BY number_of_loans DESC;


-- Q3. How many loans were approved each year, and for how much?
SELECT
    approval_year,
    COUNT(*)                            AS number_of_loans,
    ROUND(SUM(loan_amount) / 1e6, 1)    AS approved_millions
FROM loans
GROUP BY approval_year
ORDER BY approval_year;


-- Q4. Which industries hold the most money? (top 10 by NAICS sector, the first 2 digits)
-- LEFT JOIN attaches the readable sector name from our small lookup table.
-- "Not recorded" = loans where the industry code is missing.
SELECT
    COALESCE(s.sector_name, 'Not recorded')   AS industry_sector,
    COUNT(*)                                  AS number_of_loans,
    ROUND(SUM(l.loan_amount) / 1e6, 1)        AS approved_millions,
    ROUND(100.0 * SUM(l.loan_amount) / SUM(SUM(l.loan_amount)) OVER (), 1)
                                              AS percent_of_dollars
FROM loans AS l
LEFT JOIN naics_sectors AS s
       ON l.naics_sector = s.naics_sector
GROUP BY industry_sector
ORDER BY approved_millions DESC
LIMIT 10;


-- Q5. Which states hold the most money? (top 10)
SELECT
    state,
    COUNT(*)                            AS number_of_loans,
    ROUND(SUM(loan_amount) / 1e6, 1)    AS approved_millions,
    ROUND(100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER (), 1)
                                        AS percent_of_dollars
FROM loans
GROUP BY state
ORDER BY approved_millions DESC
LIMIT 10;


-- Q6. A first rough look at losses: how many loans were charged off, and how many dollars were lost?
-- (This is only a first look. In Step 3 we measure it properly, because loans
--  that are still active haven't had a chance to default yet.)
SELECT
    COUNT(*) FILTER (WHERE loan_status = 'CHGOFF')                       AS charged_off_loans,
    ROUND(100.0 * COUNT(*) FILTER (WHERE loan_status = 'CHGOFF') / COUNT(*), 2)
                                                                         AS percent_charged_off,
    ROUND(SUM(charge_off_amount) / 1e6, 1)                               AS dollars_lost_millions
FROM loans;
