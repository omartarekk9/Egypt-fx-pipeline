"""Run the pipeline:  extract -> transform -> validate -> load.

    python run_pipeline.py --backfill 365   # first run: load the last year
    python run_pipeline.py                  # daily run: load missing days (incl. recent gaps)

Exit code is 1 if ANY day failed, so a scheduler / CI job sees the failure.
Days the source simply doesn't have (HTTP 404) are logged as warnings and don't fail the run.
"""
import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from src import load
from src.extract import SourceMissingError, fetch_day
from src.transform import transform
from src.validate import validate_frame

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(Path(__file__).with_name("pipeline.log"))],
)
log = logging.getLogger("fx")


def main() -> int:
    parser = argparse.ArgumentParser(description="Egypt FX pipeline")
    parser.add_argument("--backfill", type=int, default=0, help="load the last N days")
    parser.add_argument("--lookback", type=int, default=7,
                        help="daily mode: also retry missing days in the last N days")
    args = parser.parse_args()

    conn = load.connect()
    try:
        loaded = load.get_loaded_dates(conn)
        today = date.today()

        if args.backfill:
            start = today - timedelta(days=args.backfill)
        elif loaded:
            # catch up after downtime AND heal recent gaps (a failed day before a good one)
            start = min(max(loaded) + timedelta(days=1), today - timedelta(days=args.lookback))
        else:
            start = today

        days = [start + timedelta(n) for n in range((today - start).days + 1)]
        days = [d for d in days if d not in loaded]
        log.info("Days to load: %d", len(days))

        ok = failed = missing = 0
        for d in days:
            try:
                df = transform(fetch_day(d))
                for warning in validate_frame(df):
                    log.warning("%s: %s", d, warning)  # loaded, but flagged
                rows = load.upsert(conn, df)
                ok += 1
                log.info("Loaded %s (%d rows)", d, rows)
            except SourceMissingError as error:  # the source has no file for that day: not our bug
                missing += 1
                log.warning("Missing at source %s: %s", d, error)
            except Exception as error:  # one bad day shouldn't stop the others...
                failed += 1
                log.error("FAILED %s: %s", d, error)  # ...but the run must still fail

        log.info("Done. loaded=%d failed=%d missing_at_source=%d", ok, failed, missing)
        return 1 if failed else 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
