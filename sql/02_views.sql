/* Analytical views. Run after the first load. */
USE FXTracker;
GO

-- Daily rates + change %, moving averages, volatility (window functions)
CREATE OR ALTER VIEW vw_fx_daily AS
WITH base AS (
    SELECT f.rate_date, f.currency_code, c.currency_name, c.region, c.regime, f.egp_per_unit,
           LAG(f.egp_per_unit) OVER (PARTITION BY f.currency_code ORDER BY f.rate_date) AS prev_rate
    FROM fact_fx_rate f
    JOIN dim_currency c ON c.currency_code = f.currency_code
),
chg AS (
    SELECT *, 100.0 * (egp_per_unit - prev_rate) / NULLIF(prev_rate, 0) AS daily_change_pct
    FROM base
)
SELECT rate_date, currency_code, currency_name, region, regime, egp_per_unit, prev_rate,
       ROUND(daily_change_pct, 4) AS daily_change_pct,
       ROUND(AVG(egp_per_unit) OVER (PARTITION BY currency_code ORDER BY rate_date
                 ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 4)  AS ma_7d,
       ROUND(AVG(egp_per_unit) OVER (PARTITION BY currency_code ORDER BY rate_date
                 ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 4) AS ma_30d,
       ROUND(STDEV(daily_change_pct) OVER (PARTITION BY currency_code ORDER BY rate_date
                 ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 4) AS volatility_30d,
       CASE WHEN ABS(daily_change_pct) >= 2 THEN 1 ELSE 0 END    AS is_big_move   -- >= 2% in a day
FROM chg;
GO

-- Month summary: open / close / min / max / change %
CREATE OR ALTER VIEW vw_fx_monthly AS
WITH m AS (
    SELECT *,
           FIRST_VALUE(egp_per_unit) OVER (PARTITION BY currency_code, YEAR(rate_date), MONTH(rate_date)
                                           ORDER BY rate_date) AS month_open,
           LAST_VALUE(egp_per_unit)  OVER (PARTITION BY currency_code, YEAR(rate_date), MONTH(rate_date)
                                           ORDER BY rate_date
                                           ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS month_close
    FROM fact_fx_rate
)
SELECT YEAR(rate_date) AS [year], MONTH(rate_date) AS [month], currency_code,
       MIN(egp_per_unit) AS lowest, MAX(egp_per_unit) AS highest, AVG(egp_per_unit) AS average,
       MAX(month_open) AS opening, MAX(month_close) AS closing,
       ROUND(100.0 * (MAX(month_close) - MAX(month_open)) / MAX(month_open), 2) AS month_change_pct
FROM m
GROUP BY YEAR(rate_date), MONTH(rate_date), currency_code;
GO
