import requests

from src import extract


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_falls_back_to_second_host_when_cdn_is_down(monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append(url)
        if "cdn.jsdelivr.net" in url:
            raise requests.ConnectionError("CDN down")
        return FakeResponse({"date": "2026-10-02", "usd": {"egp": 50}})

    monkeypatch.setattr(extract.requests, "get", fake_get)
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)

    data = extract.fetch_rates("2026-10-02")
    assert data["date"] == "2026-10-02"
    assert "currency-api.pages.dev" in calls[-1]


def test_raises_when_both_hosts_fail(monkeypatch):
    def always_fail(url, timeout):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(extract.requests, "get", always_fail)
    monkeypatch.setattr(extract.time, "sleep", lambda s: None)

    try:
        extract.fetch_rates("2026-10-02", retries=1)
        assert False, "should have raised"
    except RuntimeError as error:
        assert "Could not fetch" in str(error)
