"""Run the pipeline:  extract -> transform -> load.

    python run_pipeline.py --backfill 365   # first run: load the last year
    python run_pipeline.py                  # daily run: load only missing days
"""
import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

from src import load
from src.extract import fetch_rates
from src.transform import transform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(Path(__file__).with_name("pipeline.log"))],
)
log = logging.getLogger("fx")


def main() -> int:
    parser = argparse.ArgumentParser(description="Egypt FX pipeline")
    parser.add_argument("--backfill", type=int, default=0, help="load the last N days")
    args = parser.parse_args()

    conn = load.connect()
    loaded = load.get_loaded_dates(conn)
    today = date.today()

    if args.backfill:
        start = today - timedelta(days=args.backfill)
    elif loaded:
        start = max(loaded) + timedelta(days=1)   # catches up if the PC was off
    else:
        start = today

    days = [start + timedelta(n) for n in range((today - start).days + 1)]
    days = [d for d in days if d not in loaded]
    log.info("Days to load: %d", len(days))

    ok = failed = 0
    for d in days:
        key = "latest" if d == today else d.isoformat()
        try:
            rows = load.upsert(conn, transform(fetch_rates(key)))
            ok += 1
            log.info("Loaded %s (%d rows)", d, rows)
        except Exception as error:  # keep going: one bad day shouldn't stop the run
            failed += 1
            log.warning("Skipped %s: %s", d, error)

    log.info("Done. loaded=%d failed=%d", ok, failed)
    conn.close()
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    sys.exit(main())
