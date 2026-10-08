/* Egypt FX Tracker - schema (SQL Server). Run once in SSMS. */
IF DB_ID('FXTracker') IS NULL CREATE DATABASE FXTracker;
GO
USE FXTracker;
GO

CREATE TABLE dim_currency (
    currency_code CHAR(3)     PRIMARY KEY,
    currency_name VARCHAR(40) NOT NULL,
    region        VARCHAR(20) NOT NULL,
    regime        VARCHAR(20) NOT NULL        -- how the currency is managed vs USD
);

INSERT INTO dim_currency VALUES
 ('USD', 'US Dollar',          'Global',  'Reserve currency'),
 ('EUR', 'Euro',               'Europe',  'Floating'),
 ('GBP', 'British Pound',      'Europe',  'Floating'),
 ('SAR', 'Saudi Riyal',        'Gulf',    'USD peg'),
 ('AED', 'UAE Dirham',         'Gulf',    'USD peg'),
 ('QAR', 'Qatari Riyal',       'Gulf',    'USD peg'),
 ('KWD', 'Kuwaiti Dinar',      'Gulf',    'Basket peg');

CREATE TABLE fact_fx_rate (
    rate_date     DATE          NOT NULL,
    currency_code CHAR(3)       NOT NULL REFERENCES dim_currency(currency_code),
    egp_per_unit  DECIMAL(18,6) NOT NULL CHECK (egp_per_unit > 0),   -- 1 unit of currency = ? EGP
    loaded_at     DATETIME2     NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT PK_fact_fx_rate PRIMARY KEY (rate_date, currency_code)
);
GO
