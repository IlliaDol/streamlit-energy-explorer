# ⚡ Strompreis-Explorer — Day-Ahead power prices for DE-LU / AT / FR

[![CI](https://github.com/IlliaDol/streamlit-energy-explorer/actions/workflows/ci.yml/badge.svg)](https://github.com/IlliaDol/streamlit-energy-explorer/actions/workflows/ci.yml)

**English** · [Deutsch](README.de.md)

What the German electricity market actually pays, hour by hour — and what that
means for a household bill.

## Why this exists

Germany's day-ahead market produced **negative prices in 6.1% of all hours**
between 2024 and 2026 (48,455 hourly observations, mean 95.38 EUR/MWh,
range −499.99 to +936.28). That is not a curiosity: it is the reason dynamic
tariffs exist and the reason a dishwasher has become a scheduling problem.
This project turns the open data behind it into something readable.

## Results (2024-01-01 → 2026-09-10, DE-LU)

| metric | value |
|---|---|
| hourly observations | 48,455 |
| mean price | **95.38 EUR/MWh** |
| negative-price hours | **6.1 %** |
| minimum / maximum | −499.99 / +936.28 EUR/MWh |
| worst single day | 2025-11-25 (49 negative-price hours) |

Analyses: negative-price calendar, cheapest 3-hour window per day, spike-day
ranking, intraday shape ("duck curve") by month, cross-zone spread DE-LU vs FR,
and a flat-vs-dynamic tariff simulator with three household load profiles.

## Quickstart

```bash
python -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[all]"
python -c "from energy.ingest import backfill_zone; backfill_zone('DE-LU','2024-01-01','2024-12-31')"
streamlit run app.py
pytest -q      # 53 tests, no network required
```

## Data

Fraunhofer ISE **Energy-Charts API** (`https://api.energy-charts.info/price`),
no API key. Licensed **CC BY 4.0**, source attribution *Bundesnetzagentur |
SMARD.de* — see [data/LICENSE.md](data/LICENSE.md). Nothing is scraped.

## Layout

```
src/energy/client.py     HTTP + JSON -> typed PriceSeries (retries, UA)
src/energy/ingest.py     month-by-month backfill -> parquet
src/energy/features.py   UTC hygiene, DST-aware calendar features, price flags
src/energy/analysis.py   negative share, spikes, cheapest windows, duck curve
src/energy/simulate.py   load profiles + flat-vs-dynamic tariff comparison
src/energy/forecast.py   seasonal-naive vs gradient boosting, rolling-origin
src/energy/atlas.py      multi-zone comparison
app.py                   Streamlit UI (DE)
```

## Honest limitations

- The 15-minute resolution of the API's newest data is downsampled to hourly.
- The tariff simulator uses historical prices — it is a model, not advice.
- Forecasting is a baseline study: seasonal-naive is strong on hourly prices
  and is reported alongside the model, not hidden behind it.

## Method

See [docs/METHODOLOGY.md](docs/METHODOLOGY.md) and [docs/ZONES.md](docs/ZONES.md).
