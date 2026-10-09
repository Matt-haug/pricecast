"""Fetch a year of prices and drivers from the ENTSO-E Transparency Platform.

Optional: needs `entsoe-py` (``pip install pricecast[entsoe]``) and a free API
security token, read from the ``token`` argument or the ``ENTSOE_TOKEN``
environment variable. Register on transparency.entsoe.eu and request the token
in your account settings.

What is fetched, as in the paper: the day-ahead price (EUR/MWh), actual total
load (MW), and actual solar and wind generation (MW, onshore and offshore wind
summed), each averaged to hourly on a UTC index covering the local calendar
year (Central European time).

Known traps, handled or refused rather than passed on silently:

* Germany's price zone is DE-LU since 1 October 2018; earlier years were priced
  in DE-AT-LU and are refused here.
* Poland published day-ahead prices in PLN from March 2017 to November 2019;
  those years are refused rather than mixed with EUR.
* Any year whose mean price exceeds 300 EUR/MWh outside 2022 raises a warning:
  that is the signature of an unconverted currency.
"""

from __future__ import annotations

import os
import warnings

import pandas as pd

MARKET_TZ = "Europe/Brussels"
PRICE_ZONE = {"DE": "DE_LU"}


def _client(token: str | None):
    try:
        from entsoe import EntsoePandasClient
    except ImportError as exc:  # pragma: no cover - depends on the extra
        raise ImportError("fetching needs entsoe-py: pip install pricecast[entsoe]") from exc
    key = token or os.environ.get("ENTSOE_TOKEN")
    if not key:
        raise ValueError("no ENTSO-E token: pass token= or set ENTSOE_TOKEN")
    return EntsoePandasClient(api_key=key)


def _hourly(series: pd.Series) -> pd.Series:
    out = series.astype(float).sort_index()
    out = out[~out.index.duplicated(keep="first")]
    out.index = pd.DatetimeIndex(out.index).tz_convert("UTC")
    return out.resample("h").mean().interpolate(method="time")


def fetch_year(country: str, year: int, token: str | None = None
               ) -> tuple[pd.Series, pd.DataFrame]:
    """Hourly day-ahead price and drivers for one country and calendar year.

    Returns ``(prices, drivers)``: prices in EUR/MWh, drivers a frame with
    ``load``, ``solar`` and ``wind`` in MW, both on a UTC index.
    """
    country = country.upper()
    if country == "DE" and year < 2019:
        raise ValueError("German prices before 2019 straddle the DE-AT-LU split; not supported")
    if country == "PL" and 2017 <= year <= 2019:
        raise ValueError("Polish prices for 2017-2019 were partly published in PLN; not supported")

    client = _client(token)
    start = pd.Timestamp(f"{year}-01-01", tz=MARKET_TZ)
    end = pd.Timestamp(f"{year + 1}-01-01", tz=MARKET_TZ)

    prices = _hourly(client.query_day_ahead_prices(PRICE_ZONE.get(country, country),
                                                   start=start, end=end))
    window = (prices.index >= start.tz_convert("UTC")) & (prices.index < end.tz_convert("UTC"))
    prices = prices[window]
    if prices.mean() > 300.0 and year != 2022:
        warnings.warn(f"{country} {year}: mean price {prices.mean():.0f} EUR/MWh "
                      "looks like an unconverted currency", stacklevel=2)

    load = client.query_load(country, start=start, end=end)
    load = load["Actual Load"] if "Actual Load" in load.columns else load.iloc[:, 0]

    generation = client.query_generation(country, start=start, end=end)
    if isinstance(generation.columns, pd.MultiIndex):
        keep = [c for c in generation.columns if c[1] == "Actual Aggregated"]
        generation = generation[keep]
        generation.columns = [c[0] for c in keep]
    lower = {c: str(c).lower() for c in generation.columns}
    solar = generation[[c for c, n in lower.items() if "solar" in n]].sum(axis=1, min_count=1)
    wind = generation[[c for c, n in lower.items() if "wind" in n]].sum(axis=1, min_count=1)

    drivers = pd.DataFrame({"load": _hourly(load), "solar": _hourly(solar),
                            "wind": _hourly(wind)})
    index = prices.index
    drivers = drivers.reindex(index).interpolate(method="time").ffill().bfill()
    return prices.rename("price_eur_mwh"), drivers
