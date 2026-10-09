[![PyPI version](https://img.shields.io/pypi/v/pricecast?label=PyPI)](https://pypi.org/project/pricecast/)
[![Documentation Status](https://img.shields.io/readthedocs/pricecast)](https://pricecast.readthedocs.io/en/latest/)
[![Build Status](https://github.com/Matt-haug/pricecast/actions/workflows/tests.yml/badge.svg)](https://github.com/Matt-haug/pricecast/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/Matt-haug/pricecast)](https://github.com/Matt-haug/pricecast/blob/main/LICENSE)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.23264988-blue)](https://doi.org/10.5281/zenodo.23264988)

# pricecast

**Synthetic hourly electricity price years for prospective energy system studies.**

`pricecast` generates a full year of hourly day-ahead electricity prices from
three drivers - load, solar and wind generation - with a regression fitted on
recent market years. You give it the drivers of the year you want, it gives you
8760 prices in EUR/MWh, ready to feed an LP or MILP design model.

## What it is for

You are sizing or operating something that buys or sells electricity by the
hour - a heat pump with a thermal store, a battery, rooftop PV, an electrolyser
- for a year that has not happened yet, and you need a price year to optimise
against. The usual stand-in is a past year reused as it was, which carries the
past's solar fleet, the past's price level and the past's weather.

`pricecast` builds the year from what a scenario provides instead:

- **installed solar and wind, and annual demand**, which set the shape of the
  year - how deep prices fall at midday, how high they climb in the evening;
- **a price level**, which you set from a fuel-and-carbon scenario or a market
  study;
- **one weather year**, which you also use for your asset's PV output and heat
  demand, so that prices and demand respond to the same sun, wind and cold.

It is **not a forecaster**. Nobody has next decade's hourly weather, so it does
not predict the price of a given hour. It produces a plausible year for a
scenario, and leaves the level to you.

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

## A year for a future target

```python
# 1. scale one weather year's drivers to the target year's fleet and demand
future = pricecast.scale_drivers(drivers, solar=1.4, wind=1.4, load=1.3)

# 2. generate the shape of the year
year = model.predict(future)

# 3. check how far the model is extrapolating, and floor the year if it is
share = pricecast.share_beyond_training(future, training_drivers)   # % of hours
floor = pricecast.training_floor(training_prices) if share > 1.0 else None

# 4. set the level from your scenario
year = pricecast.rescale_to_level(year, level=85.0, floor=floor)
```

The scaling factors and the level come from your scenario; the
[recipe](https://pricecast.readthedocs.io/en/latest/recipe/) explains each step
and where to find the inputs (ERAA, TYNDP, fuel and carbon prices).
`pricecast.gas_plant_cost` and `pricecast.level_ratio` help build a level from
fuel and carbon prices.

## Good practice

- **One weather year for everything.** Take the model's drivers and your
  asset's PV output, heat demand and ambient temperature from the same year.
- **Noise off for sizing.** `predict(..., noise=True)` adds a residual process
  that restores price spikes and negative hours, but in hours that do not line
  up with the real ones. Use it for revenue and risk estimates, not to size
  equipment.
- **Set the level from outside, and when unsure, err low.** A design sized on
  too high a level overvalues flexibility.
- **Watch the extrapolation.** The model is linear in its drivers. When a
  scenario takes solar or wind far beyond the training years, check
  `share_beyond_training`, floor the year with `training_floor`, and count how
  many hours end up on the floor. When that becomes a large share, use the
  scenario's own hourly prices instead.
- **Day-ahead only** - not intraday, balancing or forward markets.

## Documentation

- [Usage](https://pricecast.readthedocs.io/en/latest/usage/): data formats,
  fitting, generating, checking a year's structure.
- [Recipe](https://pricecast.readthedocs.io/en/latest/recipe/): a future year
  step by step, with sources for every input.
- [Mathematics](https://pricecast.readthedocs.io/en/latest/mathematics/): the
  model, the residual process, the level and the floor.
- [`examples/`](examples/): a quick start and a complete future year.

## Data

The shipped models are fitted on ENTSO-E Transparency Platform data for
2024-2025: day-ahead prices, actual total load and actual generation per
production type. Only the fitted coefficients ship; the raw series are
downloaded with your own token.

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
