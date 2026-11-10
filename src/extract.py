"""EXTRACT: download one day of FX rates (base = USD) from the free currency-api.

Source: https://github.com/fawazahmed0/exchange-api  (free, no API key, CC0)
Two hosts are tried (CDN first, then fallback), as the API docs recommend.

Error model:
  * SourceMissingError - the source has no file for that day (HTTP 404 on every host).
    Permanent, so it is NOT retried.
  * RuntimeError       - transient problems (timeouts, 5xx, bad JSON) that survived the retries.
"""
import time
from datetime import date

import requests

PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{day}/v1/currencies/usd.json"
FALLBACK = "https://{day}.currency-api.pages.dev/v1/currencies/usd.json"


class SourceMissingError(RuntimeError):
    """The source has no data for this day. Retrying will not help."""


def fetch_rates(day: str = "latest", retries: int = 3) -> dict:
    """Return the raw JSON for `day` ('latest' or 'YYYY-MM-DD')."""
    hosts = (PRIMARY.format(day=day), FALLBACK.format(day=day))
    last_error = None
    not_found = 0

    for url in hosts:
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=20)
                if getattr(response, "status_code", None) == 404:
                    not_found += 1
                    break  # permanent for this host: don't retry, try the next host
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as error:
                last_error = error
                if attempt < retries - 1:  # no point sleeping after the last attempt
                    time.sleep(1.5 * (attempt + 1))

    if not_found == len(hosts):
        raise SourceMissingError(f"No data at the source for {day}")
    raise RuntimeError(f"Could not fetch rates for {day}: {last_error}")


def fetch_day(day: date) -> dict:
    """Fetch the rates for exactly `day`.

    Never uses 'latest': that alias can serve an older day (e.g. yesterday), which would be
    stored under the wrong date while the log says today. If the source does not have this
    exact day yet, SourceMissingError is raised.
    """
    payload = fetch_rates(day.isoformat())
    if payload.get("date") != day.isoformat():
        raise SourceMissingError(
            f"Source returned {payload.get('date')!r} when {day.isoformat()} was requested"
        )
    return payload
