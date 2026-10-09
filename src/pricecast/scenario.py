"""Building a future year: scale the drivers, set the level, check the reach.

The recipe (see docs/recipe.md):

1. fit on the two most recent complete years;
2. take every weather-dependent input from one weather year;
3. scale that year's drivers to the target year (`scale_drivers`);
4. run the model;
5. set the level from a fuel-and-carbon scenario (`gas_plant_cost`,
   `level_ratio`) and rescale to it (`rescale_to_level`), erring low;
6. check how far the model is extrapolating (`share_beyond_training`) and floor
   the year if it is far (`training_floor`).
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from .model import DriverInput, as_utc

# A combined-cycle gas plant: net efficiency, and tonnes of CO2 per MWh of
# natural gas burnt (IPCC default 56.1 t/TJ).
CCGT_EFFICIENCY = 0.55
GAS_EMISSION_FACTOR = 0.202


def gas_plant_cost(gas_eur_mwh, co2_eur_t, efficiency: float = CCGT_EFFICIENCY,
                   emission_factor: float = GAS_EMISSION_FACTOR):
    """Running cost of a gas plant, EUR per MWh of electricity.

    C = p_gas / eta + e * p_CO2 / eta, where p_gas is the gas price (EUR per MWh
    of fuel), p_CO2 the carbon price (EUR/t), eta the plant efficiency and e the
    CO2 emitted per MWh of gas burnt.
    """
    return gas_eur_mwh / efficiency + co2_eur_t * emission_factor / efficiency


def level_ratio(mean_price: float, gas_eur_mwh: float, co2_eur_t: float, **kw) -> float:
    """A market's mean price over the gas plant's running cost in the same year.

    In 2023-25 this was 0.66-0.96 in Belgium, Germany, France and Spain and
    1.06-1.13 in Poland, where coal sets the price. Multiply the latest ratio by
    a target year's cost to get its level -- and err low: the ratio drifts down
    as solar and nuclear grow, and an overestimated level costs a design far
    more than an underestimated one.
    """
    return float(mean_price) / float(gas_plant_cost(gas_eur_mwh, co2_eur_t, **kw))


def mid_year_capacity(start_of_year: float, later: float, years_between: float) -> float:
    """Capacity in the middle of a year, between its start and a later figure.

    Installed capacity is usually reported at the start of a year, while the
    year's generation comes from a fleet that kept growing through it.
    """
    return start_of_year + (later - start_of_year) * 0.5 / years_between


def scale_drivers(drivers: DriverInput, solar: float = 1.0, wind: float = 1.0,
                  load: float = 1.0) -> pd.DataFrame:
    """The weather year's hourly drivers, scaled to a target year.

    The factors are ratios: target-year over weather-year installed solar and
    wind capacity, and target-year over weather-year annual demand. The
    capacities must describe what the driver series measure -- a solar series
    that leaves out self-consumption needs a target without rooftop PV too.
    """
    out = pd.DataFrame({k: as_utc(pd.Series(drivers[k])) for k in ("load", "solar", "wind")})
    return out.assign(load=out["load"] * load, solar=out["solar"] * solar,
                      wind=out["wind"] * wind)


def net_load(drivers: DriverInput) -> pd.Series:
    """Load minus solar minus wind, MW: what the rest of the system must cover."""
    return (as_utc(pd.Series(drivers["load"])) - as_utc(pd.Series(drivers["solar"]))
            - as_utc(pd.Series(drivers["wind"])))


def share_beyond_training(drivers: DriverInput, training_drivers: DriverInput) -> float:
    """Percent of hours whose net load is lower than any the model was fitted on.

    The model is linear in its drivers, so there it keeps lowering the midday
    price where a real market stops at the price at which renewables curtail.
    Under about one percent the year can be used as is; at several percent,
    floor it.
    """
    lowest = float(net_load(training_drivers).min())
    return 100.0 * float((net_load(drivers) < lowest).mean())


def training_floor(prices: pd.Series, quantile: float = 0.01) -> float:
    """A price floor: the training years' low quantile, EUR/MWh."""
    return float(as_utc(prices).quantile(quantile))


def rescale_to_level(prices: pd.Series, level: float, floor: float | None = None,
                     weights: pd.Series | None = None) -> pd.Series:
    """Rescale a generated year so its mean is `level`, optionally floored.

    Without a floor the year is multiplied by level / mean. With one, the scale
    is chosen so that the year *after* clipping at the floor has the required
    mean -- the level is met exactly either way. Pass the hourly load as
    `weights` to match a load-weighted mean, which is how scenario studies such
    as TYNDP report their prices.
    """
    values = prices.to_numpy(dtype=float)
    w = (np.ones_like(values) if weights is None
         else weights.reindex(prices.index).to_numpy(dtype=float))
    if not np.all(np.isfinite(w)) or w.sum() <= 0.0:
        raise ValueError("weights must cover every hour of the series and sum to more than zero")
    mean = float(np.average(values, weights=w))
    if floor is None:
        if mean == 0.0:
            raise ValueError("cannot rescale a series whose mean is zero")
        return pd.Series(values * (level / mean), index=prices.index, name=prices.name)

    def clipped_mean(scale: float) -> float:
        return float(np.average(np.maximum(scale * values, floor), weights=w))

    if clipped_mean(0.0) > level:
        raise ValueError(f"the floor {floor} alone already exceeds the level {level}")
    low, high = 0.0, 1.0
    while clipped_mean(high) < level:
        high *= 2.0
        if high > 1e9:
            raise ValueError("no scale reaches the level; is the series mostly negative?")
    for _ in range(100):
        middle = 0.5 * (low + high)
        low, high = (middle, high) if clipped_mean(middle) < level else (low, middle)
    return pd.Series(np.maximum(high * values, floor), index=prices.index, name=prices.name)
