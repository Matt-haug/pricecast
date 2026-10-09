# Building a future year: the recipe

A study made years ahead has no price history for its target year. What it
does have is a scenario: installed solar and wind, annual demand, fuel and
carbon prices. The recipe turns those into an hourly price year whose *shape*
comes from the model and whose *level* comes from the scenario.

## The six steps

### 1. Fit on recent years

Fit on the two most recent complete years, or start from a shipped model
(`pricecast.load`). Older windows give coefficients from a smaller solar fleet;
a window where 2022 is a large share gives a model of a gas crisis.

```python
model = pricecast.fit([prices_2024, prices_2025], [drivers_2024, drivers_2025])
```

### 2. Choose one weather year, and take everything weather-dependent from it

The model's solar, wind and load shapes, **and** the asset's PV output, heat
demand and the ambient temperature behind its heat-pump COP all come from the
same weather year. Prices respond to the same weather: a sunny hour is cheap
because it is sunny, a cold windless evening is dear because it is cold and
windless. Pairing a price year with another year's heat demand made heat look
2-10% cheaper in the five markets tested, and cut its correlation with price by
0.03-0.12. (The solar value factor barely moves, because the clock and the
season set most of it.)

### 3. Scale the drivers

Each hour's solar and wind by the ratio of target-year to weather-year
installed capacity, each hour's load by the ratio of annual demands:

```python
future = pricecast.scale_drivers(drivers_2025, solar=s, wind=w, load=d)
```

Two things to get right:

- **Capacity at mid-year.** Installed capacity is usually reported at the start
  of a year, while the year's generation comes from a fleet that kept growing
  through it. `mid_year_capacity(start, later, years_between)` interpolates.
- **Like for like.** The capacities must describe what the driver series
  measure. Spain's ENTSO-E solar series leaves out self-consumption, so its
  residential rooftop PV must be left out of the target as well.

### 4. Run the model

```python
year = model.predict(future)
```

Keep `noise=False` for sizing. The residual noise restores the share of
negative hours, but in hours uncorrelated with the real ones, which leads a
sizing optimiser to buy for spikes that will not come.

### 5. Set the level from outside, and err low

Anchor the level on the running cost of a combined-cycle gas plant,

$$C = \frac{p_{\mathrm{gas}}}{\eta} + \frac{e\,p_{\mathrm{CO_2}}}{\eta},
\qquad \bar p = k\,C$$

where $C$ is the plant's running cost (EUR/MWh of electricity), $p_{\mathrm{gas}}$
the gas price (EUR/MWh of fuel), $p_{\mathrm{CO_2}}$ the carbon price (EUR/t),
$\eta = 0.55$ the plant's efficiency, $e = 0.202$ t of CO$_2$ per MWh of gas
burnt, $\bar p$ the mean day-ahead price of the target year, and $k$ the market's
most recent ratio of mean price to $C$.

```python
k = pricecast.level_ratio(mean_price_2025, gas_2025, co2_2025)
level = k * pricecast.gas_plant_cost(gas_2030, co2_2030)
year = pricecast.rescale_to_level(year, level)
```

In 2023-25 the ratio was 0.66-0.96 in Belgium, Germany, France and Spain and
1.06-1.13 in Poland, where coal sets the price. Predicting 2025 from 2024's
ratio and 2025's fuel and carbon prices missed by -9 to +3%; across the
2021-23 regime changes it missed by up to 41%. The ratio is drifting down where
solar and nuclear are growing, and an overestimated level makes flexibility look
more valuable than it is - a 30% overestimate cost a household design about five
times what a 30% underestimate did. **If in doubt, err low.**

**Past about 2030 the anchor stops working.** As carbon climbs and gas plants
run fewer hours, they set the price less often and the mean comes loose from
their running cost: against the TYNDP 2026 market model, the anchor was 24-282%
too high for 2035-2050 in the five countries tested. For those years take the
level from a scenario's market model instead. TYNDP reports a load-weighted mean
price per country and target year; match it as one:

```python
year = pricecast.rescale_to_level(model.predict(future), tyndp_level,
                                  floor=floor, weights=future["load"])
```

### 6. Check how far the model is extrapolating

```python
share = pricecast.share_beyond_training(future, drivers_2024_2025)
if share > 1.0:
    floor = pricecast.training_floor(prices_2024_2025, 0.01)
    year = pricecast.rescale_to_level(model.predict(future), level, floor=floor)
```

The model is linear in its drivers. Where solar or wind roughly doubles, many
hours have a net load (load minus solar minus wind) lower than anything in
training, and the model keeps lowering the midday price where a real market
stops at the price at which renewables curtail. Under about one percent of
hours, use the year as is; at several percent, floor it, or choose a nearer
target year. The model also has no storage driver, so the batteries a scenario
expects will not compress its spreads: read future spreads as upper bounds.

Also count the hours that end up **on the floor**. Built from TYNDP 2026 out to
2050, the year's 90% price quantile stayed within 25% of the TYNDP market
model's in 17 of 20 country-years, but by 2040 a quarter to half of the hours
in Germany, France, Spain and Poland sat beyond the training net load and on
the floor - far more than the market model, which builds batteries,
electrolysers and demand response alongside the panels. While both shares stay
at a few percent, use the year; past that, use the scenario's own hourly prices.

## Where the inputs come from

| input | up to about five years ahead | further ahead |
|---|---|---|
| price level | exchange futures for power, TTF gas and EU allowances | fuel and CO$_2$ prices of [ERAA 2025](https://www.entsoe.eu/eraa/2025/modelling-data/) (to 2035); the [TYNDP 2026 scenarios](https://2026.entsos-tyndp-scenarios.eu/) market-model prices per country (NT+ KPI dashboard: load-weighted mean and 10% and 90% quantiles, 2030-2050); IEA *World Energy Outlook 2025*; [EU Reference Scenario 2020](https://energy.ec.europa.eu/system/files/2021-07/eu_reference_scenario_2020_final_report_0.pdf) |
| installed solar and wind, annual demand | [ERAA 2025](https://www.entsoe.eu/eraa/2025/modelling-data/) dashboard raw data, per bidding zone (2028-2035); national energy and climate plans | [TYNDP 2026 scenarios](https://2026.entsos-tyndp-scenarios.eu/) (2030-2050) |
| hourly weather shapes | ENTSO-E generation of a past year (`pricecast.entsoe.fetch_year`) | the Pan-European Climate Database (PECD v4.2, Copernicus): historical and projected capacity factors and climate variables |
| historical fuel prices, for the ratio $k$ | World Bank Commodity Price Data, "Natural gas, Europe", at ECB annual exchange rates; EEX primary-market auction prices for EU allowances | |

## Reusing a past year instead

If you do reuse a past price year, lay it on the target year so that both start
at the same local hour (`pricecast.lay_on_calendar`). For Central European
markets a calendar year opens at 23:00 UTC on 31 December. Laid on an index
that starts at 00:00 UTC, every reused hour lands one hour late - an error that
cost the reused year a fifth of its storage value in the paper's tests before it
was caught.
