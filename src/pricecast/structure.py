"""The features of a price year that a design optimiser reacts to.

A sizing or dispatch model does not react to the mean price. It reacts to how
deep the price falls at midday, how far it climbs in the evening, how often it
goes negative, what a solar or a heating kilowatt-hour is worth against the
average one, and the spread a battery sees across a day. `structure_metrics`
measures those on any price series, so a generated year can be checked against
a real one feature by feature.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .model import as_utc

METRICS = ("Mean (EUR/MWh)", "Negative hours (%)", "Midday / mean (-)",
           "Evening - midday (EUR/MWh)", "Solar value factor (-)",
           "Daily 4h spread (EUR/MWh)", "Heat-weighted / mean (-)")


def structure_metrics(prices: pd.Series, solar: pd.Series | None = None,
                      heat: pd.Series | None = None,
                      timezone: str = "Europe/Brussels",
                      midday: Sequence[int] = range(11, 16),
                      evening: Sequence[int] = range(18, 22)) -> dict[str, float]:
    """Mean, negative-hour share, duck-curve depth, evening ramp, solar value
    factor, daily spread and heat-weighted price of one price year.

    The clock-based features are read in `timezone`. `solar` (any hourly solar
    output) and `heat` (any hourly heat demand) are optional weights; leave them
    out and those features are NaN.
    """
    price = as_utc(prices).dropna()
    local = price.tz_convert(timezone)
    hour = local.index.hour
    mean = float(local.mean())
    mid = local[np.isin(hour, list(midday))]
    eve = local[np.isin(hour, list(evening))]
    spread = local.groupby(local.index.date).apply(
        lambda day: np.sort(day.to_numpy())[-4:].mean() - np.sort(day.to_numpy())[:4].mean())

    def weighted(weights: pd.Series | None) -> float:
        if weights is None:
            return float("nan")
        w = as_utc(weights).reindex(price.index).fillna(0.0)
        return float((w * price).sum() / w.sum()) / mean

    return {
        "Mean (EUR/MWh)": mean,
        "Negative hours (%)": 100.0 * float((local < 0).mean()),
        "Midday / mean (-)": float(mid.mean()) / mean,
        "Evening - midday (EUR/MWh)": float(eve.mean() - mid.mean()),
        "Solar value factor (-)": weighted(solar),
        "Daily 4h spread (EUR/MWh)": float(spread.mean()),
        "Heat-weighted / mean (-)": weighted(heat),
    }


def compare(series: Mapping[str, pd.Series], truth: str, solar: pd.Series | None = None,
            heat: pd.Series | None = None, **kw) -> pd.DataFrame:
    """The features of several price years, with each one's gap to `truth`."""
    rows = {name: structure_metrics(s, solar, heat, **kw) for name, s in series.items()}
    table = pd.DataFrame(rows).T
    gaps = (table - table.loc[truth]).add_suffix(" gap")
    return pd.concat([table, gaps], axis=1)


def lay_on_calendar(history: pd.Series, target_index: pd.DatetimeIndex) -> pd.Series:
    """Lay a past year on a target year's hours, position by position.

    This is how a past price year is reused as a profile. Both must start at the
    same local hour -- normally local midnight on 1 January, which is 23:00 UTC
    on 31 December for Central European markets. Laying a year that starts at
    local midnight onto an index that starts an hour later shifts every hour by
    one; check the result's average-day peak against the original's.
    """
    values = history.dropna().to_numpy(dtype=float)
    repeats = int(np.ceil(len(target_index) / values.size))
    return pd.Series(np.tile(values, repeats)[: len(target_index)], index=target_index)
