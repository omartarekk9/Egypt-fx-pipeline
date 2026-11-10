from datetime import date

import pandas as pd
import pytest

from src.transform import transform
from src.validate import DataValidationError, validate_frame

TODAY = date(2026, 10, 5)


def payload(**overrides):
    usd = {"egp": 48.0, "eur": 0.85, "gbp": 0.74, "sar": 3.75,
           "aed": 3.6725, "kwd": 0.307, "qar": 3.64}
    usd.update(overrides)
    return {"date": "2026-10-01", "usd": usd}


@pytest.fixture
def good_df():
    return transform(payload())


def test_good_day_passes_with_no_warnings(good_df):
    assert validate_frame(good_df, today=TODAY) == []


def test_missing_currency_is_rejected(good_df):
    with pytest.raises(DataValidationError, match="expected 7 rows"):
        validate_frame(good_df.iloc[:-1], today=TODAY)


def test_duplicate_currency_is_rejected(good_df):
    df = pd.concat([good_df, good_df.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataValidationError, match="duplicate"):
        validate_frame(df, today=TODAY)


def test_null_rate_is_rejected(good_df):
    good_df.loc[2, "egp_per_unit"] = None
    with pytest.raises(DataValidationError, match="null"):
        validate_frame(good_df, today=TODAY)


def test_non_positive_rate_is_rejected(good_df):
    good_df.loc[1, "egp_per_unit"] = -1.0
    with pytest.raises(DataValidationError, match="non-positive"):
        validate_frame(good_df, today=TODAY)


def test_future_date_is_rejected():
    bad = payload()
    bad["date"] = "2026-12-01"
    with pytest.raises(DataValidationError, match="future"):
        validate_frame(transform(bad), today=TODAY)


def test_broken_peg_is_a_warning_not_a_failure():
    warnings = validate_frame(transform(payload(sar=3.80)), today=TODAY)
    assert len(warnings) == 1 and "SAR" in warnings[0]
