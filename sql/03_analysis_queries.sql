/* Analysis queries - run one at a time and write the findings in the README. */
USE FXTracker;
GO

-- A) Latest rate and 30-day change for every currency
WITH ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY currency_code ORDER BY rate_date DESC) AS rn
    FROM fact_fx_rate
)
SELECT l.currency_code, l.rate_date AS latest_date, l.egp_per_unit AS latest_rate,
       ROUND(100.0 * (l.egp_per_unit - p.egp_per_unit) / p.egp_per_unit, 2) AS change_30d_pct
FROM ranked l
JOIN ranked p ON p.currency_code = l.currency_code AND p.rn = 31
WHERE l.rn = 1
ORDER BY change_30d_pct DESC;

-- B) Ten biggest single-day moves of the pound against the dollar
SELECT TOP 10 rate_date, egp_per_unit, daily_change_pct
FROM vw_fx_daily
WHERE currency_code = 'USD' AND daily_change_pct IS NOT NULL
ORDER BY ABS(daily_change_pct) DESC;

-- C) Best and worst months for the pound (a positive change = the dollar got MORE expensive)
SELECT [year], [month], opening, closing, month_change_pct
FROM vw_fx_monthly
WHERE currency_code = 'USD'
ORDER BY month_change_pct DESC;

-- D) Peg check: SAR and AED are tied to USD, so implied SAR-per-USD should be flat (~3.75)
SELECT MIN(u.egp_per_unit / s.egp_per_unit) AS min_implied_sar_per_usd,
       MAX(u.egp_per_unit / s.egp_per_unit) AS max_implied_sar_per_usd
FROM fact_fx_rate u
JOIN fact_fx_rate s ON s.rate_date = u.rate_date AND s.currency_code = 'SAR'
WHERE u.currency_code = 'USD';

-- E) Data quality: missing days (gaps larger than 1 day)
WITH d AS (
    SELECT rate_date, LAG(rate_date) OVER (ORDER BY rate_date) AS prev_date
    FROM fact_fx_rate WHERE currency_code = 'USD'
)
SELECT prev_date, rate_date, DATEDIFF(DAY, prev_date, rate_date) AS gap_days
FROM d WHERE DATEDIFF(DAY, prev_date, rate_date) > 1;

-- F) Which currency is the most volatile right now? (last 30-day volatility)
SELECT currency_code, MAX(volatility_30d) AS volatility_30d
FROM vw_fx_daily
WHERE rate_date = (SELECT MAX(rate_date) FROM fact_fx_rate)
GROUP BY currency_code
ORDER BY volatility_30d DESC;
