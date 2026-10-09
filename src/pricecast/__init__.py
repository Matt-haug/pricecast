"""pricecast -- synthetic hourly electricity price years for prospective studies.

A full year of hourly day-ahead prices, generated in one shot from three
physical drivers -- load, solar and wind generation -- by a regression fitted
on recent years. It is built to be an *input* to LP and MILP design studies
(heat pumps, batteries, thermal stores, electrolysers), not to forecast
tomorrow's price.

    import pricecast

    model = pricecast.fit(prices, drivers)            # or pricecast.load("BE")
    year = model.predict(future_drivers)              # the shape of the year
    year = pricecast.rescale_to_level(year, level=80) # the level, from outside

What it is for
--------------
Because the price is driven by physical quantities, a scenario can be posed
directly: double the solar fleet, grow the demand, and read off what happens to
the *shape* of the price year -- the midday trough, the evening ramp, the value
of a solar kilowatt-hour. The level of the year is set from outside, from a
fuel-and-carbon scenario, because it cannot be extrapolated from price history.

What it is not
--------------
Not a forecaster: there are no future solar and wind series to forecast from.
It smooths away part of the midday price collapse in solar-heavy markets and
produces too few negative hours unless its residual noise is switched on --
which should stay off for sizing. It is linear in its drivers, so far outside
the range it was fitted on it must be floored (`share_beyond_training`).
"""

from __future__ import annotations

from .features import DEFAULT_FEATURES, DRIVERS, design_matrix
from .model import PriceModel, fit, residual_noise
from .pretrained import available, load
from .scenario import (
    CCGT_EFFICIENCY,
    GAS_EMISSION_FACTOR,
    gas_plant_cost,
    level_ratio,
    mid_year_capacity,
    net_load,
    rescale_to_level,
    scale_drivers,
    share_beyond_training,
    training_floor,
)
from .structure import METRICS, compare, lay_on_calendar, structure_metrics

__version__ = "0.1.0"

__all__ = [
    "CCGT_EFFICIENCY", "DEFAULT_FEATURES", "DRIVERS", "GAS_EMISSION_FACTOR",
    "METRICS", "PriceModel", "available", "compare", "design_matrix", "fit",
    "gas_plant_cost", "lay_on_calendar", "level_ratio", "load",
    "mid_year_capacity", "net_load", "rescale_to_level", "residual_noise",
    "scale_drivers", "share_beyond_training", "structure_metrics",
    "training_floor", "__version__",
]
