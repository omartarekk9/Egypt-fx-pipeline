from datetime import date

import pytest
import requests

from src import extract


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_404_on_every_host_raises_source_missing_without_retrying(monkeypatch):
    calls = []
    monkeypatch.setattr(extract.requests, "get",
                        lambda url, timeout: calls.append(url) or FakeResponse(404))
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)

    with pytest.raises(extract.SourceMissingError):
        extract.fetch_rates("2025-12-10")

    assert len(calls) == 2  # one attempt per host, no retries


def test_server_errors_are_retried_then_fallback_succeeds(monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        return FakeResponse(500) if "jsdelivr" in url else FakeResponse(200, {"date": "2026-10-01"})

    monkeypatch.setattr(extract.requests, "get", fake_get)
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)

    assert extract.fetch_rates("2026-10-01") == {"date": "2026-10-01"}
    assert sum("jsdelivr" in u for u in calls) == 3  # primary retried 3 times


def test_persistent_server_errors_raise_runtime_error_not_source_missing(monkeypatch):
    monkeypatch.setattr(extract.requests, "get", lambda url, timeout: FakeResponse(503))
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)

    with pytest.raises(RuntimeError) as info:
        extract.fetch_rates("2026-10-01")
    assert not isinstance(info.value, extract.SourceMissingError)


def test_fetch_day_rejects_a_payload_with_a_different_date(monkeypatch):
    # the source answered with yesterday's file when we asked for today
    monkeypatch.setattr(extract, "fetch_rates", lambda day: {"date": "2026-11-09", "usd": {}})
    with pytest.raises(extract.SourceMissingError, match="2026-11-09"):
        extract.fetch_day(date(2026, 11, 10))


def test_fetch_day_returns_the_payload_when_the_date_matches(monkeypatch):
    payload = {"date": "2026-11-10", "usd": {}}
    monkeypatch.setattr(extract, "fetch_rates", lambda day: payload)
    assert extract.fetch_day(date(2026, 11, 10)) is payload
