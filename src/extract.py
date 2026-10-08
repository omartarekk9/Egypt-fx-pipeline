"""EXTRACT: download one day of FX rates (base = USD) from the free currency-api.

Source: https://github.com/fawazahmed0/exchange-api  (free, no API key, CC0)
Two hosts are tried (CDN first, then fallback), as the API docs recommend.
"""
import time

import requests

PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{day}/v1/currencies/usd.json"
FALLBACK = "https://{day}.currency-api.pages.dev/v1/currencies/usd.json"


def fetch_rates(day: str = "latest", retries: int = 3) -> dict:
    """Return the raw JSON for `day` ('latest' or 'YYYY-MM-DD')."""
    last_error = None
    for url in (PRIMARY.format(day=day), FALLBACK.format(day=day)):
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as error:
                last_error = error
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch rates for {day}: {last_error}")
