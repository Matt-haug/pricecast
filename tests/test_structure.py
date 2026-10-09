import numpy as np
import pandas as pd
import pytest

import pricecast


def duck_year():
    index = pd.date_range("2024-12-31 23:00", periods=8760, freq="h", tz="UTC")
    local_hour = index.tz_convert("Europe/Brussels").hour.to_numpy()
    price = np.where((local_hour >= 11) & (local_hour <= 15), 20.0, 100.0)
    price[(local_hour >= 18) & (local_hour <= 21)] = 150.0
    price[local_hour == 19] = 180.0   # one clear peak, so the clock is testable
    return pd.Series(price, index=index)


def test_metrics_of_a_known_duck():
    s = duck_year()
    m = pricecast.structure_metrics(s)
    assert m["Midday / mean (-)"] == pytest.approx(20.0 / s.mean())
    assert m["Evening - midday (EUR/MWh)"] == pytest.approx(137.5)
    assert m["Negative hours (%)"] == 0.0
    assert m["Daily 4h spread (EUR/MWh)"] == pytest.approx(137.5)
    assert np.isnan(m["Solar value factor (-)"])


def test_solar_weighting_finds_the_midday_price():
    s = duck_year()
    local_hour = s.index.tz_convert("Europe/Brussels").hour
    solar = pd.Series(((local_hour >= 11) & (local_hour <= 15)).astype(float), index=s.index)
    m = pricecast.structure_metrics(s, solar=solar)
    assert m["Solar value factor (-)"] == pytest.approx(20.0 / s.mean())


def test_lay_on_calendar_keeps_the_clock_when_both_start_at_local_midnight():
    past = duck_year()
    target = pd.date_range("2025-12-31 23:00", periods=8760, freq="h", tz="UTC")
    laid = pricecast.lay_on_calendar(past, target)
    def peak(s):
        local = s.tz_convert("Europe/Brussels")
        return local.groupby(local.index.hour).mean().idxmax()
    assert peak(laid) == peak(past)


def test_compare_reports_gaps_to_the_truth():
    s = duck_year()
    table = pricecast.compare({"truth": s, "flat": s * 0 + s.mean()}, truth="truth")
    assert table.loc["truth", "Mean (EUR/MWh) gap"] == 0.0
    assert table.loc["flat", "Evening - midday (EUR/MWh) gap"] == pytest.approx(-137.5)
