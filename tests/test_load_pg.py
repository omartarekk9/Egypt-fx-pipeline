import pytest

from src import load_pg
from src.transform import transform

PAYLOAD = {"date": "2026-10-01",
           "usd": {"egp": 48.0, "eur": 0.85, "gbp": 0.74, "sar": 3.75,
                   "aed": 3.6725, "kwd": 0.307, "qar": 3.64}}


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def executemany(self, sql, params):
        if self.conn.fail:
            raise RuntimeError("db exploded")
        self.conn.executed.append((sql, list(params)))


class FakeConn:
    def __init__(self, fail=False):
        self.fail = fail
        self.executed = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_upsert_uses_on_conflict_and_commits():
    conn = FakeConn()
    rows = load_pg.upsert(conn, transform(PAYLOAD))

    sql, params = conn.executed[0]
    assert "ON CONFLICT (rate_date, currency_code)" in sql
    assert rows == 7 and len(params) == 7
    assert conn.commits == 1 and conn.rollbacks == 0


def test_upsert_rolls_back_and_reraises_on_failure():
    conn = FakeConn(fail=True)
    with pytest.raises(RuntimeError, match="db exploded"):
        load_pg.upsert(conn, transform(PAYLOAD))
    assert conn.rollbacks == 1 and conn.commits == 0


def test_connect_requires_a_password(monkeypatch):
    # an empty value (not a deleted one) stops load_dotenv() from filling it in from a real .env file
    monkeypatch.setenv("POSTGRES_PASSWORD", "")
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        load_pg.connect()
