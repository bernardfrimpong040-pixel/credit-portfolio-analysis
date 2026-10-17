-- ============================================================================
-- STEP 7: PEER BENCHMARKING (comparing like with like)
-- Run with:  python scripts/run_sql.py sql/07_peer_benchmarking.sql
--
-- THE PROBLEM: Step 4 found that small loans fail much more often than big
-- ones, and Step 3 found that 2005-2008 loans failed much more often than
-- others. So a lender that made lots of small loans in 2006 will look bad
-- even if it lent carefully. Comparing raw default rates is unfair.
--
-- THE FIX: "actual vs expected"
--   1. Put every loan in a box by: approval year x loan size x industry
--      (10 years x 5 sizes x 21 industries = up to 1,050 boxes).
--   2. Work out the default rate of ALL lenders together in each box.
--      That is the "peer rate" for that kind of loan.
--   3. For each lender, add up the peer rates of its own loans. That is how
--      many defaults the lender would have had if it did exactly as well as
--      its peers on the same kind of loans: its EXPECTED defaults.
--   4. Compare: performance index = actual defaults / expected defaults
--        1.00 -> exactly like peers
--        1.20 -> 20% more defaults than peers on the same kind of loans
--        0.80 -> 20% fewer
--
-- IS THE DIFFERENCE REAL OR LUCK? A lender with few loans can be above 1 by
-- chance. A common rule of thumb for counts: the difference is "clear" when
--   |actual - expected|  is bigger than  2 x square root of expected.
--   Example: expected 400 defaults -> square root 20 -> 2 x 20 = 40.
--            Actual 460 is 60 more than expected. 60 > 40, so it is clear.
-- (Never type a semicolon inside a comment in these files: run_sql.py
--  splits the file into queries at every semicolon.)
--
-- Loans approved 2001-2010 (same as Step 4).
-- ============================================================================


-- Q1. The 15 largest lenders (and KeyBank): raw vs fair comparison
WITH w AS (
    SELECT *, COALESCE(lender, 'Not recorded') AS lender_name
    FROM loans_clean
    WHERE approval_year BETWEEN 2001 AND 2010
),
boxes AS (                                   -- step 2: the peer rate in each box
    SELECT
        approval_year, loan_size_band, sector_name,
        AVG(is_default)                          AS peer_default_rate,
        SUM(charge_off_amount) / SUM(loan_amount) AS peer_loss_rate
    FROM w
    GROUP BY approval_year, loan_size_band, sector_name
),
scored AS (                                  -- step 3: give each loan its peer rate
    SELECT
        w.lender_name, w.loan_amount, w.is_default, w.charge_off_amount,
        b.peer_default_rate                       AS expected_default,
        b.peer_loss_rate * w.loan_amount          AS expected_loss
    FROM w
    JOIN boxes AS b USING (approval_year, loan_size_band, sector_name)
),
portfolio AS (
    SELECT AVG(is_default) AS portfolio_default_rate FROM w
),
by_lender AS (
    SELECT
        lender_name,
        COUNT(*)                                       AS number_of_loans,
        SUM(loan_amount)                               AS dollars,
        AVG(loan_amount)                               AS average_loan,
        SUM(is_default)                                AS actual_defaults,
        SUM(expected_default)                          AS expected_defaults,
        SUM(charge_off_amount) / SUM(expected_loss)    AS loss_index
    FROM scored
    GROUP BY lender_name
),
ranked AS (
    SELECT *, RANK() OVER (ORDER BY dollars DESC) AS size_rank
    FROM by_lender
    WHERE lender_name <> 'Not recorded'
)
SELECT
    r.size_rank,
    r.lender_name,
    r.number_of_loans,
    ROUND(r.average_loan / 1000, 0)                              AS average_loan_thousands,
    ROUND(100.0 * r.actual_defaults / r.number_of_loans, 1)      AS actual_default_pct,
    ROUND(100.0 * r.expected_defaults / r.number_of_loans, 1)    AS expected_default_pct,
    -- RAW index: lender's default rate / whole portfolio's (the unfair comparison)
    ROUND((1.0 * r.actual_defaults / r.number_of_loans) / p.portfolio_default_rate, 2)
                                                                 AS raw_index,
    -- FAIR index: actual / expected (same kind of loans)
    ROUND(r.actual_defaults / r.expected_defaults, 2)            AS performance_index,
    ROUND(r.loss_index, 2)                                       AS loss_index,
    CASE
        WHEN r.actual_defaults - r.expected_defaults >  2 * SQRT(r.expected_defaults)
             THEN 'Worse than peers'
        WHEN r.actual_defaults - r.expected_defaults < -2 * SQRT(r.expected_defaults)
             THEN 'Better than peers'
        ELSE 'In line with peers'
    END                                                          AS verdict
FROM ranked AS r
CROSS JOIN portfolio AS p
WHERE r.size_rank <= 15
   OR r.lender_name ILIKE '%KEYBANK%'        -- always include KeyBank
ORDER BY r.size_rank;


-- Q2. KeyBank close up: actual vs expected for each loan size
-- (ILIKE '%KEYBANK%' finds any lender name containing "KEYBANK", any case)
WITH w AS (
    SELECT * FROM loans_clean WHERE approval_year BETWEEN 2001 AND 2010
),
boxes AS (
    SELECT approval_year, loan_size_band, sector_name,
           AVG(is_default) AS peer_default_rate
    FROM w
    GROUP BY approval_year, loan_size_band, sector_name
)
SELECT
    w.loan_size_band,
    COUNT(*)                                                     AS keybank_loans,
    ROUND(100.0 * AVG(w.is_default), 1)                          AS actual_default_pct,
    ROUND(100.0 * AVG(b.peer_default_rate), 1)                   AS expected_default_pct,
    ROUND(SUM(w.is_default) / SUM(b.peer_default_rate), 2)       AS performance_index
FROM w
JOIN boxes AS b USING (approval_year, loan_size_band, sector_name)
WHERE w.lender ILIKE '%KEYBANK%'
GROUP BY w.loan_size_band
ORDER BY w.loan_size_band;


-- Q3. States, compared fairly (revisits Step 4)
-- Step 4 warned that some states may look risky only because of WHEN or WHAT
-- they lent. Here each state is compared with peers on the same year, loan
-- size and industry.
WITH w AS (
    SELECT * FROM loans_clean
    WHERE approval_year BETWEEN 2001 AND 2010 AND state IS NOT NULL
),
boxes AS (
    SELECT approval_year, loan_size_band, sector_name,
           AVG(is_default) AS peer_default_rate
    FROM w
    GROUP BY approval_year, loan_size_band, sector_name
),
portfolio AS (SELECT AVG(is_default) AS portfolio_default_rate FROM w),
by_state AS (
    SELECT
        w.state,
        COUNT(*)                  AS number_of_loans,
        SUM(w.loan_amount)        AS dollars,
        SUM(w.is_default)         AS actual_defaults,
        SUM(b.peer_default_rate)  AS expected_defaults
    FROM w
    JOIN boxes AS b USING (approval_year, loan_size_band, sector_name)
    GROUP BY w.state
)
SELECT
    s.state,
    s.number_of_loans,
    ROUND(100.0 * s.actual_defaults / s.number_of_loans, 1)              AS actual_default_pct,
    ROUND(100.0 * s.expected_defaults / s.number_of_loans, 1)            AS expected_default_pct,
    ROUND((1.0 * s.actual_defaults / s.number_of_loans) / p.portfolio_default_rate, 2) AS raw_index,
    ROUND(s.actual_defaults / s.expected_defaults, 2)                    AS performance_index,
    CASE
        WHEN s.actual_defaults - s.expected_defaults >  2 * SQRT(s.expected_defaults) THEN 'Worse than peers'
        WHEN s.actual_defaults - s.expected_defaults < -2 * SQRT(s.expected_defaults) THEN 'Better than peers'
        ELSE 'In line with peers'
    END                                                                  AS verdict
FROM by_state AS s
CROSS JOIN portfolio AS p
ORDER BY s.dollars DESC
LIMIT 15;
