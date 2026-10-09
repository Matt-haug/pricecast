[![PyPI version](https://img.shields.io/pypi/v/pricecast)](https://pypi.org/project/pricecast/)
[![Documentation Status](https://img.shields.io/readthedocs/loadcast)](https://pricecast.readthedocs.io/en/latest/)
[![Build Status](https://github.com/Matt-haug/pricecast/actions/workflows/tests.yml/badge.svg)](https://github.com/Matt-haug/pricecast/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/Matt-haug/pricecast)](https://github.com/Matt-haug/pricecast/blob/main/LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23264989-blue)](https://doi.org/10.5281/zenodo.23264989)

# pricecast

**Synthetic hourly electricity price time-series for prospective energy system studies**

```python
import pricecast
from pricecast.entsoe import fetch_year

prices, drivers = fetch_year("BE", 2025)          # day-ahead price, load, solar, wind
model = pricecast.load("BE")                      # or pricecast.fit(prices, drivers)

future = pricecast.scale_drivers(drivers, solar=1.39, wind=1.38, load=1.30)
year = model.predict(future)                      # the shape of a 2030 year
year = pricecast.rescale_to_level(year, level=88) # its level, from a fuel-and-carbon scenario
```

Returns an hourly series of day-ahead prices in EUR/MWh, ready to feed an LP or
MILP design model: a heat pump with storage, a battery, a thermal store, an
electrolyser.

![The average day of 2025: the model keeps the duck curve that a reused year cannot know about](https://raw.githubusercontent.com/Matt-haug/pricecast/main/docs/figures/daily_shape_2025.png)

*The average day of 2025, each series over its own annual mean. The model (fitted
on 2023-24, driven by 2025's load, solar and wind) keeps the midday trough;
reusing a past year cannot know about the panels installed since.*

## Why

A study that sizes equipment for 2030 needs a 2030 price year. The usual
stand-in is a past year reused as it was, which carries the past's solar fleet,
the past's price level, and the past's weather. `pricecast` instead generates the
year from what a scenario *does* provide - installed solar and wind, demand and
fuel prices - so the features a design reacts to follow the scenario:

- how deep the price falls at midday, and how far it climbs in the evening;
- what a solar kilowatt-hour is worth against the average one;
- what the electricity for a kilowatt-hour of heat costs.

The model is one least-squares regression of hourly price on the clock and on
three drivers - load, solar and wind generation - fitted on recent years. A full
year is generated in one shot, with no autoregression on the price.

**It is not a forecaster.** Nobody has next decade's hourly solar output, so it
does not compete with forecasting models. It produces a plausible *shape* and
leaves the *level* to an outside scenario, because the level is set by fuel and
carbon prices and cannot be extrapolated from price history.

## What it has been tested on

Five European markets (BE, DE, FR, ES, PL), fitted on 2023-24 and judged on 2025
by what a design optimiser decides, not by hourly error:

| | this model | last year's prices reused |
|---|---|---|
| daily storage, share of achievable arbitrage captured | 88% | 60% |
| household with PV, battery and heat pump, share of savings captured | 93% | 82% |
| sizing penalty with the price level given, data 1 / 2 / 4 / 6 years old (EUR/yr) | 2 / 29 / 16 / 7 | 8 / 94 / 147 / 198 |
| midday price / annual mean, mean absolute error across countries | 0.09 | 0.11 |
| solar value factor, mean absolute error | 0.07 | 0.11 |

Full results, and where it falls short, are in the accompanying paper.

## Building a future year

The [recipe](docs/recipe.md), in short:

1. **Fit** on the two most recent complete years, or start from `pricecast.load`.
2. **Choose one weather year** and take every weather-dependent input from it:
   the model's drivers, and your asset's PV output, heat demand and ambient
   temperature. Prices respond to the same weather; mixing years makes heat
   look 2-10% cheaper than it is.
3. **Scale the drivers** by target-over-weather-year capacity and demand
   (`scale_drivers`), from ERAA, TYNDP or national plans.
4. **Run the model** (`PriceModel.predict`).
5. **Set the level** as the market's recent ratio times a gas plant's running
   cost in the target year (`level_ratio`, `gas_plant_cost`,
   `rescale_to_level`). **Err low**: an overestimated level costs a design far
   more than an underestimated one.
6. **Check the reach** (`share_beyond_training`): where several percent of
   hours lie beyond the net load the model was fitted on, floor the year at the
   training years' 1% price quantile (`training_floor`).

![2030 built from ERAA 2025 drivers and a gas-plant level, on 2025 weather](https://raw.githubusercontent.com/Matt-haug/pricecast/main/docs/figures/year_2030.png)

*2030 from ERAA 2025 capacities and demand on 2025 weather. Germany and Poland
(13% and 7% of hours beyond the training net load) need the floor.*

## What it does not do

- **Negative hours.** It smooths away part of the midday collapse in
  solar-heavy markets: 1.8% negative hours against 5.7% in reality in 2025. The
  residual noise (`noise=True`) restores the share, but in hours uncorrelated
  with the real ones - use it for revenue estimates, never for sizing.
- **Extrapolation.** It is linear in its drivers; far beyond them it must be
  floored, and it has no storage driver, so future spreads are upper bounds.
- **Drifting coefficients.** The price response to solar steepens as the fleet
  grows. Correcting the coefficients for that was tested and does not pay;
  refit on recent years instead.
- **Other markets.** Day-ahead only - not intraday, balancing or forward.

## Install

```bash
pip install git+https://github.com/Matt-haug/pricecast
pip install "pricecast[entsoe] @ git+https://github.com/Matt-haug/pricecast"   # with ENTSO-E download
```

Requires Python 3.9+, numpy and pandas. Downloading data needs `entsoe-py` and a
free ENTSO-E Transparency Platform token, passed as `token=` or set as the
`ENTSOE_TOKEN` environment variable.

## Data

The shipped models are fitted on ENTSO-E Transparency Platform data for
2024-2025: day-ahead prices, actual total load and actual generation per
production type. What ships is the fitted coefficients only; the raw series are
not redistributed and are downloaded with your own token.

## Contributing

Issues and pull requests are welcome - see [CONTRIBUTING.md](CONTRIBUTING.md).
Reports that a generated year disagrees with a market you know well are
especially welcome. This project follows the
[Contributor Covenant](CODE_OF_CONDUCT.md). Generative AI was used in building
it; see [AI_USAGE.md](AI_USAGE.md).

## Citing

Use the "Cite this repository" button, or `CITATION.cff`. Each release is
archived on Zenodo with a DOI.

## Licence

MIT - see [LICENSE](LICENSE). Changes are recorded in [CHANGELOG.md](CHANGELOG.md).
