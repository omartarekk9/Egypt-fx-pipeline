"""LOAD (PostgreSQL): upsert rows into Postgres. Same interface as load.py.

Settings come from environment variables (or from a .env file next to run_pipeline.py):
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB   (the same names docker-compose uses)
    FX_PG_HOST (default: localhost)   FX_PG_PORT (default: 5433, the port docker-compose publishes)
"""
import os

UPSERT_SQL = """
INSERT INTO fact_fx_rate (rate_date, currency_code, egp_per_unit)
VALUES (%s, %s, %s)
ON CONFLICT (rate_date, currency_code)
DO UPDATE SET egp_per_unit = EXCLUDED.egp_per_unit, loaded_at = now();
"""


def connect():
    try:  # optional: read a local .env file if python-dotenv is installed
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is not set (put it in .env or the environment).")

    import psycopg2  # imported here so the SQL Server backend doesn't need it
    return psycopg2.connect(
        host=os.getenv("FX_PG_HOST", "localhost"),
        port=int(os.getenv("FX_PG_PORT", "5433")),
        dbname=os.getenv("POSTGRES_DB", "fxtracker"),
        user=os.getenv("POSTGRES_USER", "fx"),
        password=password,
    )


def get_loaded_dates(conn) -> set:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT rate_date FROM fact_fx_rate")
        rows = cur.fetchall()
    conn.commit()
    return {r[0] for r in rows}


def upsert(conn, df) -> int:
    """Insert new rows / update existing ones (safe to re-run any number of times)."""
    params = [(r.rate_date, r.currency_code, float(r.egp_per_unit)) for r in df.itertuples()]
    try:
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, params)
        conn.commit()
    except Exception:
        conn.rollback()  # a failed statement aborts the transaction; without this, every later day fails too
        raise
    return len(params)
