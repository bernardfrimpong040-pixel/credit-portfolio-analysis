-- ============================================================================
-- STEP 3: VINTAGE ANALYSIS (portfolio performance by approval year)
-- Run with:  python scripts/run_sql.py sql/03_vintage_analysis.sql
--
-- A "vintage" is the group of loans approved in the same year, like wine from
-- the same harvest. Comparing vintages shows whether loans made in some years
-- did much worse than others, and why.
--
-- Three measures, all in percent:
--   default rate  = share of LOANS that were charged off        (how often)
--   loss rate     = share of DOLLARS approved that were lost    (how much)
--   loss severity = for the loans that went bad, share of their
--                   approved amount that was lost               (how bad)
--
-- Check: loss rate is roughly default rate x loss severity.
--
-- All queries use loans_clean, the table built in Step 2.
-- ============================================================================


-- Q1. How long after approval do loans usually go bad?
-- We look only at OLD vintages (1989-2005), because those loans have had
-- 9+ years to show their full story. For each loan age, we count how many
-- defaults happened, then add them up as we go ("cumulative percent").
-- RESULT ON THE REAL DATA: only about 1/3 of defaults happen within 4 years,
-- about 1/2 within 5 years, and about 87% within 8 years. So a vintage needs
-- about 8 years before we can fairly judge it. Q2 uses that rule.
WITH defaults AS (
    SELECT
        -- months between approval and charge-off, turned into whole years
        LEAST(FLOOR(date_diff('month', approval_date, charge_off_date) / 12), 10)
                                            AS years_until_default
    FROM loans_clean
    WHERE is_default = 1
      AND approval_year BETWEEN 1989 AND 2005
      AND charge_off_date IS NOT NULL
)
SELECT
    CASE WHEN years_until_default = 10 THEN '10 or more'
         ELSE CAST(CAST(years_until_default AS INTEGER) AS VARCHAR) || ' to '
              || CAST(CAST(years_until_default AS INTEGER) + 1 AS VARCHAR)
    END                                                       AS loan_age_years,
    COUNT(*)                                                  AS number_of_defaults,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)        AS percent_of_defaults,
    ROUND(100.0 * SUM(COUNT(*)) OVER (ORDER BY years_until_default)
                / SUM(COUNT(*)) OVER (), 1)                   AS cumulative_percent
FROM defaults
GROUP BY years_until_default
ORDER BY years_until_default;


-- Q2. The vintage table: performance of each approval year
-- loan_age_in_2014 = how old the vintage was when the data was collected.
-- Based on Q1, each vintage gets one of three labels:
--   Seasoned           8+ years old  -> about 87% or more of its defaults have happened
--   Partly seasoned    4-7 years old -> about 1/3 to 4/5 have happened, so its
--                                       default rate is a MINIMUM (it can only go up)
--   Too young to judge under 4 years -> under 1/3 have happened
SELECT
    approval_year                                               AS vintage,
    2014 - approval_year                                        AS loan_age_in_2014,
    CASE WHEN approval_year <= 2006 THEN 'Seasoned'
         WHEN approval_year <= 2010 THEN 'Partly seasoned'
         ELSE 'Too young to judge' END                          AS seasoning,
    COUNT(*)                                                    AS number_of_loans,
    ROUND(SUM(loan_amount) / 1e6, 0)                            AS approved_millions,
    ROUND(100.0 * AVG(is_default), 1)                           AS default_rate_pct,
    ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 1) AS loss_rate_pct,
    ROUND(100.0 * SUM(charge_off_amount) FILTER (WHERE is_default = 1)
                / SUM(loan_amount)       FILTER (WHERE is_default = 1), 1)
                                                                AS loss_severity_pct
FROM loans_clean
GROUP BY approval_year
ORDER BY approval_year;


-- Q3. The same measures grouped into five "eras"
-- This turns 26 rows into 5, which is how you'd present it to leadership.
SELECT
    CASE
        WHEN approval_year <= 1999 THEN '1. 1989-1999  (1990s)'
        WHEN approval_year <= 2004 THEN '2. 2000-2004  (before the boom)'
        WHEN approval_year <= 2008 THEN '3. 2005-2008  (boom, then crisis)'
        WHEN approval_year <= 2010 THEN '4. 2009-2010  (after the crisis)'
        ELSE                            '5. 2011-2014  (too young to judge)'
    END                                                         AS era,
    COUNT(*)                                                    AS number_of_loans,
    ROUND(SUM(loan_amount) / 1e9, 1)                            AS approved_billions,
    ROUND(100.0 * AVG(is_default), 1)                           AS default_rate_pct,
    ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 1) AS loss_rate_pct,
    ROUND(SUM(charge_off_amount) / 1e9, 2)                      AS dollars_lost_billions
FROM loans_clean
GROUP BY era
ORDER BY era;


-- Q4. WHEN did the losses actually arrive? (charge-offs by calendar year)
-- Vintages tell you WHICH loans went bad. This tells you WHEN the bank felt it,
-- which is what matters for planning and for setting aside money for losses.
SELECT
    YEAR(charge_off_date)                       AS charge_off_year,
    COUNT(*)                                    AS loans_charged_off,
    ROUND(SUM(charge_off_amount) / 1e6, 0)      AS dollars_lost_millions
FROM loans_clean
WHERE is_default = 1
  AND charge_off_date IS NOT NULL
  AND YEAR(charge_off_date) BETWEEN 1989 AND 2014
GROUP BY charge_off_year
ORDER BY charge_off_year;


-- Q5. Do the flagged (odd) loans from Step 2 change the results?
-- We compare the measures WITH and WITHOUT the flagged loans.
-- If the numbers barely move, our conclusions are safe either way.
SELECT
    'All loans'                                                 AS which_loans,
    COUNT(*)                                                    AS number_of_loans,
    ROUND(100.0 * AVG(is_default), 2)                           AS default_rate_pct,
    ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 2) AS loss_rate_pct
FROM loans_clean
UNION ALL
SELECT
    'Without flagged loans',
    COUNT(*),
    ROUND(100.0 * AVG(is_default), 2),
    ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 2)
FROM loans_clean
WHERE NOT (COALESCE(flag_chgoff_no_loss, FALSE)
        OR COALESCE(flag_loss_over_amount, FALSE)
        OR COALESCE(flag_pif_with_loss, FALSE)
        OR COALESCE(flag_zero_term, FALSE));
