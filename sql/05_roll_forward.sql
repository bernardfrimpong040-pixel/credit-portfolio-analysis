-- ============================================================================
-- STEP 5: HOW LOANS MOVE BETWEEN STATUSES OVER TIME (roll-forward)
-- Run with:  python scripts/run_sql.py sql/05_roll_forward.sql
--
-- Every loan starts as PERFORMING (being repaid) and ends in one of two ways:
--   CHARGED OFF  -> the borrower stopped paying and the loss was booked
--   PAID OFF     -> the loan was repaid in full
-- Watching how loans move from the first status to the other two, and how
-- fast, is the simple version of what banks call "credit migration".
--
-- ONE LIMIT OF THIS DATA: it has the date each loan was CHARGED OFF, but not
-- the date each good loan was PAID OFF. Where we need a payoff date (Q2), we
-- use the loan's scheduled end date (approval date + term). Loans repaid early
-- are therefore counted as outstanding for too long, which makes the yearly
-- charge-off RATE in Q2 a little too LOW. The trend over time is still valid.
--
-- We use loans approved 2001 onwards, because charge-off dates before 2001
-- look incomplete (Step 3).
-- ============================================================================


-- Q1. Vintage curves: % of each vintage charged off by each loan age
-- Read across a row: how a vintage got worse as it aged.
-- Read down a column: how vintages compare AT THE SAME AGE (a fair comparison).
-- A cell is empty (NaN) when the vintage had not reached that age by 2014.
WITH loan_ages AS (
    SELECT
        approval_year,
        is_default,
        -- how many months after approval the loan was charged off
        date_diff('month', approval_date, charge_off_date) AS months_to_chargeoff
    FROM loans_clean
    WHERE approval_year BETWEEN 2001 AND 2013
)
SELECT
    approval_year AS vintage,
    COUNT(*)      AS number_of_loans,
    -- For each age: count loans charged off within that many years, divided
    -- by all loans in the vintage. "CASE WHEN approval_year + n <= 2014" leaves
    -- the cell empty if the vintage was not yet n years old in 2014.
    CASE WHEN approval_year + 1 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 12) / COUNT(*), 1) END AS age_1,
    CASE WHEN approval_year + 2 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 24) / COUNT(*), 1) END AS age_2,
    CASE WHEN approval_year + 3 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 36) / COUNT(*), 1) END AS age_3,
    CASE WHEN approval_year + 4 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 48) / COUNT(*), 1) END AS age_4,
    CASE WHEN approval_year + 5 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 60) / COUNT(*), 1) END AS age_5,
    CASE WHEN approval_year + 6 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 72) / COUNT(*), 1) END AS age_6,
    CASE WHEN approval_year + 7 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 84) / COUNT(*), 1) END AS age_7,
    CASE WHEN approval_year + 8 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 96) / COUNT(*), 1) END AS age_8,
    CASE WHEN approval_year + 9 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 108) / COUNT(*), 1) END AS age_9,
    CASE WHEN approval_year + 10 <= 2014 THEN ROUND(100.0 * COUNT(*) FILTER (WHERE is_default = 1 AND months_to_chargeoff < 120) / COUNT(*), 1) END AS age_10
FROM loan_ages
GROUP BY approval_year
ORDER BY approval_year;


-- Q2. Yearly roll-forward of the number of loans (2001-2014)
-- Like a bank statement for loans:
--   start of year + new loans - charged off - paid off = end of year
-- annual_chargeoff_rate = loans charged off this year / loans at start of year
WITH loan_lives AS (
    SELECT
        YEAR(approval_date)                                         AS start_year,
        CASE WHEN is_default = 1 THEN 'Charged off' ELSE 'Paid off' END AS exit_type,
        -- the year the loan left the portfolio
        CASE WHEN is_default = 1 THEN YEAR(charge_off_date)
             ELSE YEAR(approval_date + term_months * INTERVAL 1 MONTH)
        END                                                         AS end_year
    FROM loans_clean
    WHERE approval_year >= 2001
      AND term_months > 0                                   -- skip the 0-month loans (flagged in Step 2)
      AND NOT (is_default = 1 AND charge_off_date IS NULL)  -- need a date for every charge-off
),
years AS (
    SELECT calendar_year FROM range(2001, 2015) AS t(calendar_year)
)
SELECT
    y.calendar_year,
    COUNT(*) FILTER (WHERE l.start_year < y.calendar_year AND l.end_year >= y.calendar_year)
                                                                    AS loans_at_start,
    COUNT(*) FILTER (WHERE l.start_year = y.calendar_year)          AS new_loans,
    COUNT(*) FILTER (WHERE l.end_year = y.calendar_year AND l.exit_type = 'Charged off')
                                                                    AS charged_off,
    COUNT(*) FILTER (WHERE l.end_year = y.calendar_year AND l.exit_type = 'Paid off')
                                                                    AS paid_off,
    COUNT(*) FILTER (WHERE l.start_year <= y.calendar_year AND l.end_year > y.calendar_year)
                                                                    AS loans_at_end,
    ROUND(100.0
          * COUNT(*) FILTER (WHERE l.end_year = y.calendar_year AND l.exit_type = 'Charged off')
          / COUNT(*) FILTER (WHERE l.start_year < y.calendar_year AND l.end_year >= y.calendar_year), 2)
                                                                    AS annual_chargeoff_rate_pct
FROM years AS y
CROSS JOIN loan_lives AS l
GROUP BY y.calendar_year
ORDER BY y.calendar_year;


-- Q3. Check that the roll-forward adds up
-- For every year: start + new - charged off - paid off should equal end.
-- The "difference" column should be 0 in every row. Checking that your own
-- numbers tie out is a habit every bank analyst is expected to have.
WITH loan_lives AS (
    SELECT
        YEAR(approval_date) AS start_year,
        is_default,
        CASE WHEN is_default = 1 THEN YEAR(charge_off_date)
             ELSE YEAR(approval_date + term_months * INTERVAL 1 MONTH) END AS end_year
    FROM loans_clean
    WHERE approval_year >= 2001
      AND term_months > 0
      AND NOT (is_default = 1 AND charge_off_date IS NULL)
),
roll AS (
    SELECT
        y.calendar_year,
        COUNT(*) FILTER (WHERE start_year < calendar_year AND end_year >= calendar_year) AS at_start,
        COUNT(*) FILTER (WHERE start_year = calendar_year)                               AS new_loans,
        COUNT(*) FILTER (WHERE end_year = calendar_year)                                 AS all_exits,
        COUNT(*) FILTER (WHERE start_year <= calendar_year AND end_year > calendar_year) AS at_end
    FROM range(2001, 2015) AS y(calendar_year)
    CROSS JOIN loan_lives
    GROUP BY y.calendar_year
)
SELECT
    calendar_year,
    at_start + new_loans - all_exits AS calculated_end,
    at_end                           AS counted_end,
    at_start + new_loans - all_exits - at_end AS difference
FROM roll
ORDER BY calendar_year;


-- Q4. How EARLY in their life did loans fail? (by era)
-- For loans that were charged off, what share failed within 2, 4 and 6 years?
-- If crisis-era loans failed earlier, the crisis hit them while they were young.
WITH defaults AS (
    SELECT
        CASE
            WHEN approval_year <= 2004 THEN '1. 2001-2004 (before the boom)'
            ELSE                            '2. 2005-2008 (boom, then crisis)'
        END                                                   AS era,
        date_diff('month', approval_date, charge_off_date)    AS months_to_chargeoff
    FROM loans_clean
    WHERE is_default = 1
      AND charge_off_date IS NOT NULL
      AND approval_year BETWEEN 2001 AND 2008
)
SELECT
    era,
    COUNT(*)                                                               AS number_of_defaults,
    ROUND(MEDIAN(months_to_chargeoff) / 12.0, 1)                           AS median_years_to_chargeoff,
    ROUND(100.0 * COUNT(*) FILTER (WHERE months_to_chargeoff < 24) / COUNT(*), 1) AS pct_within_2_years,
    ROUND(100.0 * COUNT(*) FILTER (WHERE months_to_chargeoff < 48) / COUNT(*), 1) AS pct_within_4_years,
    ROUND(100.0 * COUNT(*) FILTER (WHERE months_to_chargeoff < 72) / COUNT(*), 1) AS pct_within_6_years
FROM defaults
GROUP BY era
ORDER BY era;
