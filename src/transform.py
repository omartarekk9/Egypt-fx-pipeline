"""TRANSFORM: turn the raw API payload into clean rows: 1 unit of X = ? EGP."""
import math

import pandas as pd

# Currencies we track against the Egyptian pound.
TRACKED = ["usd", "eur", "gbp", "sar", "aed", "kwd", "qar"]


def transform(payload: dict) -> pd.DataFrame:
    """Return a DataFrame with columns: rate_date, currency_code, egp_per_unit.

    The API gives "units of X per 1 USD". So:
        EGP per 1 X = (EGP per 1 USD) / (X per 1 USD)
    """
    usd = payload["usd"]

    needed = ["egp"] + [c for c in TRACKED if c != "usd"]
    missing = [c for c in needed if c not in usd]
    if missing:
        raise ValueError(f"Missing currencies in API response: {missing}")

    units_per_usd = {c: (1.0 if c == "usd" else float(usd[c])) for c in TRACKED}
    egp_per_usd = float(usd["egp"])

    for name, value in {"egp": egp_per_usd, **units_per_usd}.items():
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Invalid rate for {name}: {value}")

    df = pd.DataFrame({
        "currency_code": [c.upper() for c in TRACKED],
        "egp_per_unit": [round(egp_per_usd / units_per_usd[c], 6) for c in TRACKED],
    })
    df.insert(0, "rate_date", payload["date"])
    return df
