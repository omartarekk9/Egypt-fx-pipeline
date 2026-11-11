-- Egypt FX Tracker: PostgreSQL schema (runs automatically on the first `docker compose up`)

CREATE TABLE dim_currency (
    currency_code  CHAR(3)      PRIMARY KEY,
    currency_name  VARCHAR(50)  NOT NULL,
    region         VARCHAR(50)  NOT NULL,
    fx_regime      VARCHAR(20)  NOT NULL
        CHECK (fx_regime IN ('floating', 'USD peg', 'basket peg'))
);

CREATE TABLE fact_fx_rate (
    rate_date      DATE           NOT NULL,
    currency_code  CHAR(3)        NOT NULL REFERENCES dim_currency (currency_code),
    egp_per_unit   NUMERIC(18, 6) NOT NULL CHECK (egp_per_unit > 0),   -- 1 unit of currency = ? EGP
    loaded_at      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    PRIMARY KEY (rate_date, currency_code)   -- this key is what makes the upsert idempotent
);

INSERT INTO dim_currency (currency_code, currency_name, region, fx_regime) VALUES
    ('USD', 'US Dollar',          'United States', 'floating'),
    ('EUR', 'Euro',               'Eurozone',      'floating'),
    ('GBP', 'British Pound',      'United Kingdom','floating'),
    ('SAR', 'Saudi Riyal',        'Saudi Arabia',  'USD peg'),
    ('AED', 'UAE Dirham',         'UAE',           'USD peg'),
    ('QAR', 'Qatari Riyal',       'Qatar',         'USD peg'),
    ('KWD', 'Kuwaiti Dinar',      'Kuwait',        'basket peg');
