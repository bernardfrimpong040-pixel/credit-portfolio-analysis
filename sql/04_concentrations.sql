-- ============================================================================
-- STEP 4a: RISK CONCENTRATIONS
-- Run with:  python scripts/run_sql.py sql/04_concentrations.sql
--
-- A concentration is a lot of money in one place: one industry, one state,
-- one lender, one loan size. If that place has a bad year, a big part of the
-- portfolio suffers at once.
--
-- WHICH LOANS: every query uses loans approved 2001-2010, because
--   - industry codes are recorded for these years (Step 2 found they are
--     missing for about 55% of loans before 2001), and
--   - they are at least 4 years old, so they have had time to show risk
--     (Step 3). Loans from 2011-2014 are too young to judge.
--
-- KEY IDEA: compare two shares for each group
--   share of dollars = how much of the money lent went to this group
--   share of losses  = how much of the money LOST came from this group
--   risk index       = share of losses / share of dollars
--     risk index 1.0 -> the group loses money at the same rate as the whole portfolio
--     risk index 2.0 -> it loses twice as much as its size would suggest
--     risk index 0.5 -> it loses half as much
-- ============================================================================


-- Q1. Industry concentration and risk
WITH w AS (
    SELECT * FROM loans_clean WHERE approval_year BETWEEN 2001 AND 2010
)
SELECT
    sector_name                                                          AS industry,
    COUNT(*)                                                             AS number_of_loans,
    ROUND(SUM(loan_amount) / 1e9, 2)                                     AS approved_billions,
    ROUND(100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER (), 1)   AS pct_of_dollars,
    ROUND(100.0 * SUM(charge_off_amount)
                / SUM(SUM(charge_off_amount)) OVER (), 1)                AS pct_of_losses,
    ROUND(100.0 * AVG(is_default), 1)                                    AS default_rate_pct,
    ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 1)          AS loss_rate_pct,
    ROUND( (SUM(charge_off_amount) / SUM(SUM(charge_off_amount)) OVER ())
         / (SUM(loan_amount)       / SUM(SUM(loan_amount)) OVER ()), 2)  AS risk_index
FROM w
GROUP BY sector_name
ORDER BY pct_of_dollars DESC;


-- Q2. State concentration and risk (the 15 states with the most money)
WITH w AS (
    SELECT * FROM loans_clean WHERE approval_year BETWEEN 2001 AND 2010
),
by_state AS (
    SELECT
        COALESCE(state, 'Not recorded')                                      AS state,
        COUNT(*)                                                             AS number_of_loans,
        ROUND(SUM(loan_amount) / 1e9, 2)                                     AS approved_billions,
        ROUND(100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER (), 1)   AS pct_of_dollars,
        ROUND(100.0 * SUM(charge_off_amount)
                    / SUM(SUM(charge_off_amount)) OVER (), 1)                AS pct_of_losses,
        ROUND(100.0 * AVG(is_default), 1)                                    AS default_rate_pct,
        ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 1)          AS loss_rate_pct,
        ROUND( (SUM(charge_off_amount) / SUM(SUM(charge_off_amount)) OVER ())
             / (SUM(loan_amount)       / SUM(SUM(loan_amount)) OVER ()), 2)  AS risk_index
    FROM w
    GROUP BY COALESCE(state, 'Not recorded')
)
SELECT * FROM by_state
ORDER BY pct_of_dollars DESC
LIMIT 15;


-- Q3. Does loan size matter? (testing Step 3's finding that bad loans were smaller)
WITH w AS (
    SELECT * FROM loans_clean WHERE approval_year BETWEEN 2001 AND 2010
)
SELECT
    loan_size_band,
    COUNT(*)                                                             AS number_of_loans,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                   AS pct_of_loans,
    ROUND(100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER (), 1)   AS pct_of_dollars,
    ROUND(100.0 * AVG(is_default), 1)                                    AS default_rate_pct,
    ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 1)          AS loss_rate_pct
FROM w
GROUP BY loan_size_band
ORDER BY loan_size_band;


-- Q4. The 10 lenders with the most money in the portfolio
WITH w AS (
    SELECT * FROM loans_clean WHERE approval_year BETWEEN 2001 AND 2010
),
by_lender AS (
    SELECT
        COALESCE(lender, 'Not recorded')                                     AS lender,
        COUNT(*)                                                             AS number_of_loans,
        ROUND(100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER (), 1)   AS pct_of_dollars,
        ROUND(100.0 * AVG(is_default), 1)                                    AS default_rate_pct,
        ROUND(100.0 * SUM(charge_off_amount) / SUM(loan_amount), 1)          AS loss_rate_pct,
        ROUND( (SUM(charge_off_amount) / SUM(SUM(charge_off_amount)) OVER ())
             / (SUM(loan_amount)       / SUM(SUM(loan_amount)) OVER ()), 2)  AS risk_index
    FROM w
    GROUP BY COALESCE(lender, 'Not recorded')
)
SELECT * FROM by_lender
ORDER BY pct_of_dollars DESC
LIMIT 10;


-- Q5. One number for "how concentrated": the HHI (Herfindahl-Hirschman Index)
-- How it works: take each group's share of dollars in percent, square it, add
-- them all up.
--   Example: 4 groups with 25% each  -> 25^2 x 4         = 2,500
--            1 group with 100%       -> 100^2            = 10,000 (all eggs in one basket)
--            100 groups with 1% each -> 1^2 x 100        = 100 (very spread out)
-- US regulators call a market moderately concentrated from 1,000 and highly
-- concentrated above 1,800 (2023 Merger Guidelines). We borrow that scale.
-- equivalent_groups = 10,000 / HHI: "the portfolio is as spread out as if the
-- money were split evenly across this many groups".
WITH w AS (
    SELECT * FROM loans_clean WHERE approval_year BETWEEN 2001 AND 2010
),
shares AS (
    SELECT 'Industry' AS dimension, sector_name AS grp,
           100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER () AS share_pct
    FROM w GROUP BY sector_name
    UNION ALL
    SELECT 'State', COALESCE(state, 'Not recorded'),
           100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER ()
    FROM w GROUP BY COALESCE(state, 'Not recorded')
    UNION ALL
    SELECT 'Lender', COALESCE(lender, 'Not recorded'),
           100.0 * SUM(loan_amount) / SUM(SUM(loan_amount)) OVER ()
    FROM w GROUP BY COALESCE(lender, 'Not recorded')
)
SELECT
    dimension,
    COUNT(*)                                   AS number_of_groups,
    ROUND(MAX(share_pct), 1)                   AS largest_group_pct,
    ROUND(SUM(share_pct * share_pct), 0)       AS hhi,
    ROUND(10000 / SUM(share_pct * share_pct), 1) AS equivalent_groups,
    CASE
        WHEN SUM(share_pct * share_pct) > 1800  THEN 'Highly concentrated'
        WHEN SUM(share_pct * share_pct) >= 1000 THEN 'Moderately concentrated'
        ELSE 'Not concentrated'
    END                                        AS reading
FROM shares
GROUP BY dimension
ORDER BY hhi DESC;
