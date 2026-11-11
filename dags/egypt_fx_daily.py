"""Airflow DAG: extract -> validate -> load, one DAG run per day.

One DAG run = one rate date (the run's logical date). That is what makes it idempotent and
backfillable: re-running a day overwrites the same raw file and upserts the same 7 rows.

The tasks reuse the same modules as run_pipeline.py (src/extract, transform, validate, load_pg),
so there is no second copy of the logic.
"""
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from airflow.sdk import dag, task

log = logging.getLogger(__name__)

RAW_DIR = Path("/opt/airflow/data/raw")  # the raw layer: the untouched API response, one file per day


def _transformed(raw_path: str):
    from src.transform import transform

    return transform(json.loads(Path(raw_path).read_text()))


@dag(
    dag_id="egypt_fx_daily",
    description="Egypt FX rates: extract -> validate -> load into Postgres",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=True,        # runs every day since start_date that has not run yet
    max_active_runs=1,   # one day at a time: gentle on the API and on a small machine
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["fx"],
)
def egypt_fx_daily():
    @task
    def extract(day: str) -> str:
        """Download the exact day and keep the raw JSON, so any later step can be replayed
        without calling the API again."""
        from src.extract import fetch_day

        payload = fetch_day(date.fromisoformat(day))
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        path = RAW_DIR / f"{day}.json"
        path.write_text(json.dumps(payload))
        log.info("Saved raw payload to %s", path)
        return str(path)

    @task
    def validate(raw_path: str) -> str:
        """Fail loudly: a bad day raises, the task turns red and nothing reaches the database."""
        from src.validate import validate_frame

        for warning in validate_frame(_transformed(raw_path)):
            log.warning("%s: %s", raw_path, warning)
        return raw_path

    @task
    def load(raw_path: str) -> int:
        from src.load_pg import connect, upsert

        df = _transformed(raw_path)
        conn = connect()
        try:
            rows = upsert(conn, df)
        finally:
            conn.close()
        log.info("Upserted %d rows", rows)
        return rows

    load(validate(extract("{{ ds }}")))


egypt_fx_daily()
