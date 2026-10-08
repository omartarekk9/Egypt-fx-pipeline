"""LOAD: upsert rows into SQL Server using Windows Authentication (no password anywhere).

Override the defaults with environment variables if needed:
    FX_SQL_SERVER   (default: localhost\\SQLEXPRESS)
    FX_SQL_DATABASE (default: FXTracker)
"""
import os

import pyodbc

SERVER = os.getenv("FX_SQL_SERVER", r"localhost\SQLEXPRESS")
DATABASE = os.getenv("FX_SQL_DATABASE", "FXTracker")
PREFERRED_DRIVERS = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"]

MERGE_SQL = """
MERGE fact_fx_rate AS t
USING (SELECT CAST(? AS DATE) AS rate_date, ? AS currency_code,
              CAST(? AS DECIMAL(18,6)) AS egp_per_unit) AS s
   ON t.rate_date = s.rate_date AND t.currency_code = s.currency_code
WHEN MATCHED THEN UPDATE SET egp_per_unit = s.egp_per_unit, loaded_at = SYSDATETIME()
WHEN NOT MATCHED THEN INSERT (rate_date, currency_code, egp_per_unit)
     VALUES (s.rate_date, s.currency_code, s.egp_per_unit);
"""


def _pick_driver() -> str:
    installed = pyodbc.drivers()
    for driver in PREFERRED_DRIVERS:
        if driver in installed:
            return driver
    raise RuntimeError("No SQL Server ODBC driver found. Install 'ODBC Driver 18 for SQL Server'.")


def connect() -> "pyodbc.Connection":
    conn_str = (
        f"DRIVER={{{_pick_driver()}}};SERVER={SERVER};DATABASE={DATABASE};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


def get_loaded_dates(conn) -> set:
    rows = conn.cursor().execute("SELECT DISTINCT rate_date FROM fact_fx_rate").fetchall()
    return {r[0] for r in rows}


def upsert(conn, df) -> int:
    """Insert new rows / update existing ones (safe to re-run any number of times)."""
    params = [(r.rate_date, r.currency_code, float(r.egp_per_unit)) for r in df.itertuples()]
    cursor = conn.cursor()
    cursor.executemany(MERGE_SQL, params)
    conn.commit()
    return len(params)
