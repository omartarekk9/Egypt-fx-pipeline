"""VALIDATE: checks on one transformed day, before it reaches the warehouse.

Hard failures raise DataValidationError (the day is rejected and the run fails loudly).
Soft findings are returned as warnings (the day is loaded, but the problem is logged).
"""
import math
from datetime import date

import pandas as pd

from src.transform import TRACKED

# Fixed dollar pegs, expressed as units of currency per 1 USD.
PEGS = {"SAR": 3.75, "AED": 3.6725}
PEG_TOLERANCE = 0.005  # 0.5 %


class DataValidationError(ValueError):
    """The day's data is not safe to load."""


def validate_frame(df: pd.DataFrame, today: date | None = None) -> list[str]:
    """Return a list of warnings; raise DataValidationError if the day must be rejected."""
    today = today or date.today()
    expected = {c.upper() for c in TRACKED}
    errors: list[str] = []

    # --- row count, duplicates, missing currencies -------------------------------
    if len(df) != len(expected):
        errors.append(f"expected {len(expected)} rows, got {len(df)}")
    codes = list(df["currency_code"])
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    if dupes:
        errors.append(f"duplicate currencies: {dupes}")
    missing = sorted(expected - set(codes))
    if missing:
        errors.append(f"missing currencies: {missing}")

    # --- nulls and rate sanity ---------------------------------------------------
    if df[["rate_date", "currency_code", "egp_per_unit"]].isna().any().any():
        errors.append("null values found")
    rates = pd.to_numeric(df["egp_per_unit"], errors="coerce")
    bad = [c for c, v in zip(codes, rates) if not (math.isfinite(v) and v > 0)]
    if bad:
        errors.append(f"non-positive or non-finite rates for: {bad}")

    # --- date --------------------------------------------------------------------
    if df["rate_date"].nunique() != 1:
        errors.append("rows have different rate_date values")
    else:
        try:
            rate_date = date.fromisoformat(str(df["rate_date"].iloc[0]))
            if rate_date > today:
                errors.append(f"rate_date {rate_date} is in the future")
        except ValueError:
            errors.append(f"invalid rate_date: {df['rate_date'].iloc[0]!r}")

    if errors:
        raise DataValidationError("; ".join(errors))

    # --- soft check: Gulf pegs must hold (catches bad source data) ---------------
    warnings: list[str] = []
    by_code = dict(zip(codes, rates))
    for code, peg in PEGS.items():
        implied = by_code["USD"] / by_code[code]  # units of `code` per 1 USD
        deviation = abs(implied - peg) / peg
        if deviation > PEG_TOLERANCE:
            warnings.append(
                f"{code} peg deviates {deviation:.2%} (implied {implied:.4f} vs peg {peg})"
            )
    return warnings
