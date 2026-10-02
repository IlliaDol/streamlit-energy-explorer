import json
from pathlib import Path

import pytest

from energy.client import (
    EnergyChartsError,
    concat_series,
    fetch_json,
    fetch_prices,
    parse_prices,
    price_url,
    slice_series,
)

FIXTURE = Path(__file__).parent / "fixtures" / "price_de_lu_small.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_parse_prices_builds_utc_index():
    series = parse_prices(load_fixture(), "DE-LU")
    assert series.zone == "DE-LU"
    assert str(series.frame.index.tz) == "UTC"
    assert series.frame.index.is_monotonic_increasing
    assert list(series.frame.columns) == ["price_eur_mwh"]
    assert series.unit == "EUR / MWh"


def test_parse_prices_keeps_gaps_as_nan():
    series = parse_prices(load_fixture(), "DE-LU")
    assert series.frame["price_eur_mwh"].isna().sum() == 1


def test_parse_prices_captures_license_attribution():
    series = parse_prices(load_fixture(), "DE-LU")
    assert "CC BY 4.0" in series.license_info


def test_parse_prices_rejects_ragged_arrays():
    with pytest.raises(EnergyChartsError):
        parse_prices({"unix_seconds": [1, 2], "price": [1.0]}, "DE-LU")


def test_price_url_contains_zone_and_range():
    url = price_url("DE-LU", "2024-01-01", "2024-02-01")
    assert url.startswith("https://api.energy-charts.info/price?")
    assert "bzn=DE-LU" in url and "start=2024-01-01" in url and "end=2024-02-01" in url


class _FakeResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fetch_json_retries_then_succeeds():
    calls = {"n": 0}

    def flaky(url, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("temporary")
        return _FakeResponse({"ok": True})

    payload = fetch_json("https://example.invalid", opener=flaky, sleep=lambda _s: None)
    assert payload == {"ok": True}
    assert calls["n"] == 3


def test_fetch_json_raises_after_exhausting_retries():
    def broken(url, timeout):
        raise OSError("down")

    with pytest.raises(EnergyChartsError):
        fetch_json("https://example.invalid", opener=broken, retries=2, sleep=lambda _s: None)


def test_fetch_prices_uses_injected_opener():
    def opener(url, timeout):
        assert "bzn=DE-LU" in url
        return _FakeResponse(load_fixture())

    series = fetch_prices(opener=opener)
    assert len(series) == 4


def test_slice_series_respects_bounds():
    series = parse_prices(load_fixture(), "DE-LU")
    cut = slice_series(series, start="2024-01-01T01:00:00")
    assert len(cut) == 3


def test_concat_series_deduplicates_timestamps():
    series = parse_prices(load_fixture(), "DE-LU")
    merged = concat_series([series, series])
    assert len(merged) == len(series)
