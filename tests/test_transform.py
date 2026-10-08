import pytest

from src.transform import TRACKED, transform

PAYLOAD = {
    "date": "2026-10-02",
    "usd": {"egp": 50.0, "eur": 0.9, "gbp": 0.8, "sar": 3.75, "aed": 3.6725, "kwd": 0.3, "qar": 3.64},
}


def test_one_row_per_tracked_currency():
    df = transform(PAYLOAD)
    assert len(df) == len(TRACKED)
    assert df["currency_code"].is_unique


def test_usd_row_equals_egp_per_usd():
    df = transform(PAYLOAD).set_index("currency_code")
    assert df.loc["USD", "egp_per_unit"] == 50.0


def test_cross_rate_math():
    df = transform(PAYLOAD).set_index("currency_code")
    assert df.loc["EUR", "egp_per_unit"] == pytest.approx(50 / 0.9, rel=1e-6)
    assert df.loc["SAR", "egp_per_unit"] == pytest.approx(50 / 3.75, rel=1e-6)


def test_date_is_kept():
    assert (transform(PAYLOAD)["rate_date"] == "2026-10-02").all()


def test_missing_currency_raises():
    bad = {"date": "2026-10-02", "usd": {"egp": 50.0, "eur": 0.9}}
    with pytest.raises(ValueError, match="Missing currencies"):
        transform(bad)


@pytest.mark.parametrize("bad_value", [0, -1, float("nan")])
def test_invalid_rate_raises(bad_value):
    bad = {"date": "2026-10-02", "usd": {**PAYLOAD["usd"], "eur": bad_value}}
    with pytest.raises(ValueError, match="Invalid rate"):
        transform(bad)
