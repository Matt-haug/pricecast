<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Matt-haug/pricecast/main/docs/assets/pricecast-lockup-dark.svg">
    <img alt="pricecast" src="https://raw.githubusercontent.com/Matt-haug/pricecast/main/docs/assets/pricecast-lockup.svg" width="440">
  </picture>
</p>

[![PyPI version](https://img.shields.io/pypi/v/pricecast?label=PyPI)](https://pypi.org/project/pricecast/)
[![Documentation Status](https://img.shields.io/readthedocs/pricecast)](https://pricecast.readthedocs.io/en/latest/)
[![Build Status](https://github.com/Matt-haug/pricecast/actions/workflows/tests.yml/badge.svg)](https://github.com/Matt-haug/pricecast/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/Matt-haug/pricecast)](https://github.com/Matt-haug/pricecast/blob/main/LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23264988-blue)](https://doi.org/10.5281/zenodo.23264988)


**A parametric model of hourly electricity prices, for scenario sweeps,
uncertainty propagation and future years.**

`pricecast` turns three hourly drivers - load, solar and wind generation - into
a full year of hourly day-ahead prices: 8760 values in EUR/MWh, generated in one
shot and ready to feed an LP or MILP design model. The model is a regression
fitted on market years, so it responds to its drivers as real prices have: more
solar lowers the price in the hours when the sun shines, more wind in the windy
hours, more demand in every hour.

## What it is for

Use it when a design study needs hourly prices for a year that has not
happened, or for many such years. You are sizing or operating something that
buys or sells electricity by the hour - a heat pump with a thermal store, a
battery, rooftop PV, an electrolyser. The usual stand-in is a past price year
reused as it was, which carries the past's solar fleet, price level and
weather, and the whole study then rests on that one year.

Because the model is parametric in its drivers, it does three things a reused
year cannot:

- **Sweep a scenario.** Change one driver at a time - double the solar fleet,
  grow demand by a third - and read what happens to the midday trough, the
  evening ramp and the value of a solar kilowatt-hour. Rescaling a past year
  moves its level or stretches its spread, but every hour keeps its rank;
  scaling the drivers changes *which* hours are cheap.
- **Propagate uncertainty.** A price year takes a fraction of a second, so
  hundreds of them, one per sampled scenario, take seconds. A market model needs
  a full simulation for each.
- **Build a future year from a market-model scenario.** A scenario such as
  ENTSO-E's TYNDP 2026 supplies the fleet, the demand and the price level; the
  model supplies the hourly shape that follows from them. Where the scenario
  publishes its hourly results, fit the model on them, and it becomes a cheap
  stand-in for the market model around that scenario.

It is **not a forecaster**, and not a market model. Nobody has next decade's
hourly weather, so it does not predict the price of a given hour; and it does
not dispatch storage or demand response. The scenario carries those, through
its price level and, when the model is fitted on its hourly results, through
the coefficients.

## Install

```bash
pip install pricecast
pip install "pricecast[entsoe]"    # to download market data from ENTSO-E
```

Requires Python 3.9+, numpy and pandas.

### Getting an ENTSO-E token

Downloading market data needs a free security token from the ENTSO-E
Transparency Platform. ENTSO-E's guide is
[How to get security token?](https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token); in short:

1. Register an account on the [Transparency Platform](https://transparency.entsoe.eu/).
2. Email [transparency@entsoe.eu](mailto:transparency@entsoe.eu) with
   "Restful API access" as the subject and your registered email address in
   the body.
3. Once ENTSO-E has granted access, generate the
   token in your account settings.
4. Pass it as `token=`, or set it once as the `ENTSOE_TOKEN` environment
   variable. Keep it out of version control.

You only need a token to download data: the shipped models, `fit` on your own
series and everything else work without one.

## Quick start

```python
import pricecast
from pricecast.entsoe import fetch_year

prices, drivers = fetch_year("BE", 2025)   # day-ahead price; load, solar, wind
model = pricecast.load("BE")               # a shipped model: BE, DE, FR, ES, PL
year = model.predict(drivers)              # an hourly price year, EUR/MWh
```

Or fit your own, on any market with hourly prices and drivers:

```python
model = pricecast.fit([prices_2024, prices_2025], [drivers_2024, drivers_2025])
model.to_json("my_market.json")
```

## A future year from TYNDP

The scenario gives the target year's fleet, demand and price level; the model
gives the shape. With Belgium's 2030 figures from TYNDP 2026 (central scenario,
National Trends+):

```python
import pandas as pd

(p24, d24), (p25, d25) = fetch_year("BE", 2024), fetch_year("BE", 2025)

# 1. scale the 2025 weather year to TYNDP's 2030 fleet (GW) and demand (TWh)
solar_2025 = pricecast.mid_year_capacity(10.70, later=15.64, years_between=5)
wind_2025 = pricecast.mid_year_capacity(5.44, later=7.84, years_between=5)
future = pricecast.scale_drivers(d25, solar=15.64 / solar_2025, wind=7.84 / wind_2025,
                                 load=110.7e6 / d25["load"].sum())

# 2. generate the shape, floor it, and give it TYNDP's load-weighted mean price
floor = pricecast.training_floor(pd.concat([p24, p25]))
year = pricecast.rescale_to_level(model.predict(future), level=65.1, floor=floor,
                                  weights=future["load"])

# 3. check how far the model reaches: % of hours beyond its training net load
pricecast.share_beyond_training(future, pd.concat([d24, d25]))
```

The [recipe](https://pricecast.readthedocs.io/en/latest/recipe/) explains each
step and where every number comes from. For a target year beyond the model's
reach, or to carry TYNDP's storage and demand response into the shape, fit the
model on TYNDP's own hourly results (recipe, step 1).

## Sweeps and uncertainty

Each price year costs a matrix product, so a scenario's uncertainty can be
sampled rather than argued. For Belgium in 2035 - the solar and wind build-out
five years early or late, demand and price level between TYNDP's lower- and
higher-growth variants:

```python
import numpy as np

rng = np.random.default_rng(1)
years = []
for solar, wind, demand, level in rng.uniform([15.6, 7.8, 122.7, 38.0],
                                              [29.5, 17.6, 145.3, 109.3], size=(200, 4)):
    future = pricecast.scale_drivers(d25, solar=solar / solar_2025, wind=wind / wind_2025,
                                     load=demand * 1e6 / d25["load"].sum())
    years.append(pricecast.rescale_to_level(model.predict(future), level, floor=floor,
                                            weights=future["load"]))
```

Feed each year to your design model, and fit a polynomial chaos expansion to
its outputs to rank the inputs; the
[uncertainty page](https://pricecast.readthedocs.io/en/latest/uncertainty/)
shows how, and what to check before reading the result.

## Good practice

- **One weather year for everything.** Take the model's drivers and your
  asset's PV output, heat demand and ambient temperature from the same year, so
  that prices and demand respond to the same sun, wind and cold.
- **Noise off for sizing.** `predict(..., noise=True)` adds a residual process
  that restores price spikes and negative hours, but in hours that do not line
  up with the real ones. Use it for revenue and risk estimates, not to size
  equipment.
- **Take the level from the scenario; if unsure, choose the low end of your
  range.** Match it as a load-weighted mean (`weights=`), as TYNDP reports it.
  Rescaling multiplies every hour, so a level set too high also widens the gap
  between cheap and dear hours: flexibility looks more valuable than it is, and
  the design costs more than one sized on a level set too low by the same
  amount.
- **Watch the reach.** The model is linear in its drivers. Count the hours
  beyond its training net load (`share_beyond_training`) and the hours left on
  the floor after rescaling. While both stay at a few percent, use the year;
  past that, use the scenario's own hourly prices.
- **Read spreads as upper bounds** when the model is fitted on market years: it
  holds storage and demand response at their training-year level, while a
  scenario adds both. Fitted on the scenario's hourly results, it carries them.
- **Day-ahead only** - not intraday, balancing or forward markets.

## Documentation

- [Usage](https://pricecast.readthedocs.io/en/latest/usage/): data formats,
  fitting, generating, checking a year's structure.
- [Recipe](https://pricecast.readthedocs.io/en/latest/recipe/): a future year
  from TYNDP step by step, with sources for every input.
- [Sweeps and uncertainty](https://pricecast.readthedocs.io/en/latest/uncertainty/):
  one driver at a time, sampled scenarios, and sensitivity indices.
- [Mathematics](https://pricecast.readthedocs.io/en/latest/mathematics/): the
  model, the residual process, the level, the floor and the reach.
- [`examples/`](examples/): a quick start, a future year and a sampled scenario.

## Data

The shipped models are fitted on ENTSO-E Transparency Platform data for
2024-2025: day-ahead prices, actual total load and actual generation per
production type. Only the fitted coefficients ship; the raw series are
downloaded with your own token. The scenario figures quoted in the examples come
from the [TYNDP 2026 scenarios](https://2026.entsos-tyndp-scenarios.eu/) of
ENTSO-E and ENTSOG.

## Sister project

Does your study need hourly energy demand as well as prices?
[`loadcast`](https://loadcast.readthedocs.io/en/latest/), by the same authors,
turns a few numbers from an industrial site's energy bill into a year of hourly
heat, cold and electricity demand, with the coupling between the carriers as an
input. It follows the same idea: a few stated inputs give a year of hourly data,
fast enough to sweep and to sample.

## Citing

Use the "Cite this repository" button or [`CITATION.cff`](CITATION.cff). Every
release is archived on Zenodo:
[10.5281/zenodo.23264988](https://doi.org/10.5281/zenodo.23264988) always
points to the latest version.

## Contributing

Issues and pull requests are welcome - see [CONTRIBUTING.md](CONTRIBUTING.md).
Reports of a generated year that disagrees with a market you know well are
especially useful. This project follows the
[Contributor Covenant](CODE_OF_CONDUCT.md). Generative AI was used in building
it; see [AI_USAGE.md](AI_USAGE.md).

## Licence

MIT - see [LICENSE](LICENSE). Changes are recorded in [CHANGELOG.md](CHANGELOG.md).
