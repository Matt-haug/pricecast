<p align="center" markdown>
![pricecast](assets/pricecast-lockup.svg#only-light){ width="440" }
![pricecast](assets/pricecast-lockup-dark.svg#only-dark){ width="440" }
</p>

**A parametric model of hourly electricity prices, for scenario sweeps,
uncertainty propagation and future years.**

`pricecast` turns hourly load, solar and wind generation into a full year of
hourly day-ahead prices, in one shot. The model is a regression fitted on market
years, so its prices respond to the drivers as real prices have: a larger solar
fleet deepens the midday trough on sunny days and not on overcast ones. Each
year takes a fraction of a second, which makes the model an *input* for LP and
MILP design studies - a heat pump with storage, a battery, PV, an electrolyser -
and for the many price years that a sweep or an uncertainty propagation needs.

The model supplies the hourly shape; a scenario supplies the rest. For a future
year, ENTSO-E's TYNDP 2026 scenarios give the fleet, the demand and the price
level, and their hourly results can serve as the model's training data. It is
not a forecaster and not a market model: it does not predict a given hour, and
it does not dispatch storage or demand response.

```bash
pip install pricecast
pip install "pricecast[entsoe]"    # to download market data from ENTSO-E
```

- [Usage](usage.md): fitting, generating, checking a year's structure.
- [Recipe](recipe.md): a future year from TYNDP, step by step, with the source
  of every input.
- [Sweeps and uncertainty](uncertainty.md): one driver at a time, sampled
  scenarios, and which inputs matter.
- [Mathematics](mathematics.md): the model, the residual process, the level,
  the floor and the reach, with every symbol defined.

Does your study need hourly energy demand as well as prices? Its sister
project, [`loadcast`](https://loadcast.readthedocs.io/en/latest/), by the same
authors, turns a few numbers from an industrial site's energy bill into a year
of hourly heat, cold and electricity demand, with the coupling between the
carriers as an input.
