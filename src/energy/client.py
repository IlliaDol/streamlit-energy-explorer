"""Thin client for the Fraunhofer ISE Energy-Charts API.

Only the endpoint actually used by this project is wrapped. The client keeps
its own HTTP concerns (timeouts, retries, UA) so callers get plain pandas.
"""

from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

import pandas as pd

BASE_URL = "https://api.energy-charts.info"
USER_AGENT = "energy-explorer/0.1 (data-science portfolio; contact via GitHub IlliaDol)"
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.5


class EnergyChartsError(RuntimeError):
    """Raised when the API cannot be reached or returns something unusable."""


@dataclass(frozen=True)
class PriceSeries:
    """Day-ahead prices for one bidding zone, UTC-indexed, EUR/MWh."""

    zone: str
    unit: str
    frame: pd.DataFrame
    license_info: str = ""

    @property
    def start(self) -> pd.Timestamp:
        return self.frame.index[0]

    @property
    def end(self) -> pd.Timestamp:
        return self.frame.index[-1]

    def __len__(self) -> int:
        return len(self.frame)


def _default_opener(url: str, timeout: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout)


def fetch_json(
    url: str,
    *,
    timeout: int = 30,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    opener: Callable[[str, int], Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """GET a JSON document with retry/backoff. Raises EnergyChartsError on failure."""
    open_ = opener or _default_opener
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with open_(url, timeout) as response:  # type: ignore[operator]
                raw = response.read()
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surfaced as EnergyChartsError
            last_error = exc
            if attempt < retries - 1:
                sleep(backoff**attempt)
    raise EnergyChartsError(f"request failed after {retries} attempts: {url}") from last_error


def parse_prices(payload: dict[str, Any], zone: str) -> PriceSeries:
    """Turn a /price payload into a UTC-indexed frame.

    The API returns parallel arrays (``unix_seconds``, ``price``); missing
    prices are kept as NaN rather than dropped so gaps stay visible.
    """
    seconds = payload.get("unix_seconds") or []
    prices = payload.get("price") or []
    if len(seconds) != len(prices):
        raise EnergyChartsError("unix_seconds and price have different lengths")
    if not seconds:
        return PriceSeries(zone=zone, unit=payload.get("unit", "EUR / MWh"),
                           frame=pd.DataFrame(index=pd.DatetimeIndex([], tz="UTC"),
                                              columns=["price_eur_mwh"], dtype="float64"),
                           license_info=payload.get("license_info", ""))
    index = pd.to_datetime(seconds, unit="s", utc=True)
    frame = pd.DataFrame({"price_eur_mwh": pd.to_numeric(prices, errors="coerce")}, index=index)
    frame.index.name = "timestamp_utc"
    return PriceSeries(
        zone=zone,
        unit=payload.get("unit", "EUR / MWh"),
        frame=frame,
        license_info=payload.get("license_info", ""),
    )


def price_url(zone: str, start: str, end: str) -> str:
    return f"{BASE_URL}/price?bzn={zone}&start={start}&end={end}"


def fetch_prices(
    zone: str = "DE-LU",
    start: str = "2024-01-01",
    end: str = "2024-01-31",
    **kwargs: Any,
) -> PriceSeries:
    """Convenience wrapper: fetch + parse in one call."""
    payload = fetch_json(price_url(zone, start, end), **kwargs)
    return parse_prices(payload, zone)


def slice_series(series: PriceSeries, start: str | None = None, end: str | None = None) -> PriceSeries:
    frame = series.frame
    if start:
        frame = frame.loc[frame.index >= pd.Timestamp(start, tz="UTC")]
    if end:
        frame = frame.loc[frame.index <= pd.Timestamp(end, tz="UTC")]
    return PriceSeries(series.zone, series.unit, frame, series.license_info)


def concat_series(parts: Iterable[PriceSeries]) -> PriceSeries:
    parts = list(parts)
    if not parts:
        raise EnergyChartsError("no series to concatenate")
    zone = parts[0].zone
    frame = pd.concat([p.frame for p in parts]).sort_index()
    frame = frame[~frame.index.duplicated(keep="first")]
    return PriceSeries(zone, parts[0].unit, frame, parts[0].license_info)
