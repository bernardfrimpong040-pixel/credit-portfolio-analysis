-- ============================================================================
-- STEP 6a: EARLY WARNING INDICATORS FROM INSIDE THE PORTFOLIO
-- Run with:  python scripts/run_sql.py sql/06_early_warnings.sql
--
-- An early warning indicator is a number you can see EARLY that tells you
-- trouble is coming LATER. The question is: could an analyst have seen the
-- 2010 loss peak coming, and how many years in advance?
--
-- The idea: a vintage's EARLY default rate (how many loans failed in their
-- first 2 years) is known just 2 years after approval, long before the final
-- result. If a new vintage fails much faster than normal in its first 2
-- years, that is a warning.
--
-- BASELINE ("normal"): the average of the 2001, 2002 and 2003 vintages,
-- which were made before the boom.
-- ============================================================================


-- Q1. Early default rate of each vintage, compared with the baseline
-- age_2_pct            = % of the vintage charged off within 2 years of approval
-- year_known           = the year this number could first be seen (vintage + 2)
-- times_baseline       = age_2_pct / the baseline's age_2_pct
-- signal               = Green under 2x, Amber from 2x, Red from 3x the baseline
WITH early AS (
    SELECT
        approval_year                                                    AS vintage,
        COUNT(*)                                                         AS number_of_loans,
        100.0 * COUNT(*) FILTER (WHERE is_default = 1
              AND date_diff('month', approval_date, charge_off_date) < 24)
              / COUNT(*)                                                 AS age_2_pct,
        100.0 * COUNT(*) FILTER (WHERE is_default = 1
              AND date_diff('month', approval_date, charge_off_date) < 36)
              / COUNT(*)                                                 AS age_3_pct
    FROM loans_clean
    WHERE approval_year BETWEEN 2001 AND 2012      -- 2012 + 2 = 2014, the last year we can see
    GROUP BY approval_year
),
baseline AS (
    SELECT AVG(age_2_pct) AS base_age_2
    FROM early
    WHERE vintage BETWEEN 2001 AND 2003
)
SELECT
    e.vintage,
    e.vintage + 2                                       AS year_known,
    e.number_of_loans,
    ROUND(e.age_2_pct, 2)                               AS age_2_pct,
    ROUND(b.base_age_2, 2)                              AS baseline_age_2_pct,
    ROUND(e.age_2_pct / b.base_age_2, 1)                AS times_baseline,
    CASE
        WHEN e.age_2_pct / b.base_age_2 >= 3 THEN 'Red'
        WHEN e.age_2_pct / b.base_age_2 >= 2 THEN 'Amber'
        ELSE 'Green'
    END                                                 AS signal
FROM early AS e
CROSS JOIN baseline AS b
ORDER BY e.vintage;


-- Q2. Which INDUSTRIES got worse first?
-- For each industry, compare the 3-year default rate of loans made in
-- 2001-2002 (calm) with loans made in 2005-2006 (boom).
-- times_worse = boom rate / calm rate. The 2005-2006 numbers were known by
-- 2008-2009, so a big "times_worse" was visible before the 2010 peak.
-- We only show industries with at least 1,000 loans in each period, because
-- small groups give unreliable rates (Step 4).
WITH by_period AS (
    SELECT
        sector_name                                                      AS industry,
        CASE WHEN approval_year IN (2001, 2002) THEN 'calm' ELSE 'boom' END AS period,
        COUNT(*)                                                         AS number_of_loans,
        100.0 * COUNT(*) FILTER (WHERE is_default = 1
              AND date_diff('month', approval_date, charge_off_date) < 36)
              / COUNT(*)                                                 AS age_3_pct
    FROM loans_clean
    WHERE approval_year IN (2001, 2002, 2005, 2006)
    GROUP BY sector_name, period
)
SELECT
    calm.industry,
    calm.number_of_loans                          AS loans_2001_02,
    boom.number_of_loans                          AS loans_2005_06,
    ROUND(calm.age_3_pct, 1)                      AS age_3_pct_2001_02,
    ROUND(boom.age_3_pct, 1)                      AS age_3_pct_2005_06,
    ROUND(boom.age_3_pct / calm.age_3_pct, 1)     AS times_worse
FROM by_period AS calm
JOIN by_period AS boom
  ON calm.industry = boom.industry
 AND calm.period = 'calm'
 AND boom.period = 'boom'
WHERE calm.number_of_loans >= 1000
  AND boom.number_of_loans >= 1000
ORDER BY times_worse DESC;


-- Q3. Which STATES got worse first? (same method, states with 5,000+ loans in each period)
WITH by_period AS (
    SELECT
        state,
        CASE WHEN approval_year IN (2001, 2002) THEN 'calm' ELSE 'boom' END AS period,
        COUNT(*)                                                         AS number_of_loans,
        100.0 * COUNT(*) FILTER (WHERE is_default = 1
              AND date_diff('month', approval_date, charge_off_date) < 36)
              / COUNT(*)                                                 AS age_3_pct
    FROM loans_clean
    WHERE approval_year IN (2001, 2002, 2005, 2006)
      AND state IS NOT NULL
    GROUP BY state, period
)
SELECT
    calm.state,
    calm.number_of_loans                          AS loans_2001_02,
    boom.number_of_loans                          AS loans_2005_06,
    ROUND(calm.age_3_pct, 1)                      AS age_3_pct_2001_02,
    ROUND(boom.age_3_pct, 1)                      AS age_3_pct_2005_06,
    ROUND(boom.age_3_pct / calm.age_3_pct, 1)     AS times_worse
FROM by_period AS calm
JOIN by_period AS boom
  ON calm.state = boom.state
 AND calm.period = 'calm'
 AND boom.period = 'boom'
WHERE calm.number_of_loans >= 5000
  AND boom.number_of_loans >= 5000
ORDER BY times_worse DESC;
