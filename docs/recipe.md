# A future year from a scenario: the recipe

A study made years ahead has no price history for its target year, but it has a
scenario. The scenario supplies what a regression on past years cannot know -
the fleet, the demand and the price level - and the model supplies the hourly
shape that follows from them. This page builds the year from ENTSO-E's TYNDP
2026 scenarios, whose central scenario (National Trends+, NT+) and two variants
cover 2030 to 2050, so that the future years rest on the same organisation's
data as the past ones. `examples/02_future_year.py` runs every step for Belgium
in 2030.

## The six steps

### 1. Fit the model, on market years or on the scenario's hourly results

The coefficients decide how the price responds to the drivers, and they can come
from two places.

**On market years.** Fit on the two most recent complete years, or start from a
shipped model (`pricecast.load`, fitted on 2024-2025). Older windows give
coefficients from a smaller solar fleet, and a window where 2022 is a large
share gives a model of a gas crisis. A model fitted this way responds to solar
and wind as the market did in its training years, with the storage and demand
response of those years.

```python
model = pricecast.fit([prices_2024, prices_2025], [drivers_2024, drivers_2025])
```

**On the scenario's hourly results, preferred for a TYNDP target year.** A
scenario builds batteries, electrolysers and demand response alongside its
panels, and they lift the cheapest hours, which a model fitted on market years
cannot see. In the five markets of the accompanying study, the model fitted on
2024-2025 and driven by TYNDP's own hourly drivers placed the average day's
peaks and troughs well but overstated TYNDP's daily spread 1.5 to 4.5 times.
Fitted instead on two of TYNDP's three weather scenarios for a target year and
tested on the third, it reproduced TYNDP's average day (correlation 0.98-1.00)
and its hourly prices with a correlation of 0.62-0.88. Its tails stay too
narrow: the model is a conditional mean, so its 10% quantile sits too high and
its 90% quantile 10-45 EUR/MWh too low.

TYNDP publishes these results as
[hourly dashboards](https://2026-data.entsos-tyndp-scenarios.eu/output/model-results/hourly-dashboards/NT+_TimeSeriesDashboard.zip),
one archive per scenario (about 1.8 GB for NT+), with one workbook per country
and weather scenario. Build the three drivers and the price as TYNDP defines
them:

- **price**: the marginal costs of the country's wholesale (E-Market) and
  household (Prosumer) nodes, weighted by each node's total load, as TYNDP's
  KPI dashboard does;
- **load**: the native and fixed demand of both nodes plus electric-vehicle
  charging net of discharging. Leave out batteries, pumped storage,
  electrolysers, heat pumps and demand response, because they respond to the
  price;
- **solar** and **wind**: utility, rooftop and shared-plant PV; onshore and
  offshore wind. Add curtailment back to them in proportion to their output, so
  that they measure what the weather made available, as ENTSO-E's series do.

TYNDP's years are simulated climate years without a calendar. Read their hours
as CET, lay them on a non-leap year whose weekdays match the weekly pattern of
TYNDP's demand, and convert the index to UTC. Then leave out the scarcity hours,
priced by demand-response bands or unserved energy at 2-3 kEUR/MWh in some 2040
weather scenarios, which the model cannot produce:

```python
# prices_ws, drivers_ws: TYNDP's price and drivers for each weather scenario of
# the target year, on a UTC index
ordinary = [p.where(p < 1000.0) for p in prices_ws]    # missing hours are not fitted
model = pricecast.fit(ordinary, drivers_ws, metadata={"source": "TYNDP 2026 NT+ 2040"})
floor = pricecast.training_floor(pd.concat(ordinary))  # for step 5
```

So fitted, the model carries the scenario's storage, demand response,
interconnection and marginal-cost structure, and it can be driven by any weather
year scaled to the scenario: a cheap stand-in for the market model around its
scenario.

### 2. Choose one weather year, and take everything weather-dependent from it

The model's solar, wind and load shapes, **and** the asset's PV output, heat
demand and the ambient temperature behind its heat-pump COP all come from the
same weather year. Prices respond to the same weather: a sunny hour is cheap
because it is sunny, a cold windless evening is dear because it is cold and
windless. Pairing a price year with another year's heat demand throws that
covariance away and makes heat look cheaper than it is.

### 3. Scale the drivers

Each hour's solar and wind is scaled by the ratio of target-year to weather-year
installed capacity, and each hour's load by the ratio of annual demands:

```python
future = pricecast.scale_drivers(drivers_2025, solar=s, wind=w, load=d)
```

Two things to get right:

- **Capacity at mid-year.** ENTSO-E reports installed capacity at the start of a
  year, while the year's generation comes from a fleet that kept growing through
  it. `mid_year_capacity(start, later, years_between)` interpolates towards the
  scenario's first target year.
- **Like for like.** The scenario's figures must describe what the driver series
  measure. The load series is matched by TYNDP's native and fixed demand plus
  electric-vehicle charging. Spain's ENTSO-E solar series leaves out
  self-consumption, so its rooftop PV, listed in TYNDP's capacity inputs
  (PEMMDB), must be taken out of the target as well.

### 4. Run the model

```python
year = model.predict(future)
```

Keep `noise=False` for sizing. The residual noise restores the share of
negative hours, but in hours uncorrelated with the real ones, which leads a
sizing optimiser to buy for spikes that will not come.

### 5. Floor the year and give it the scenario's level

The level comes from the scenario's market model, as a load-weighted mean.
TYNDP's KPI dashboard reports, per country and target year, the load-weighted
mean price of its market model. Floor the year at the training prices' 1%
quantile - near the price at which a market stops falling, because renewables
curtail rather than sell lower; TYNDP's ordinary hours give it when the model
was fitted on them (step 1) - and match that mean as one:

```python
floor = pricecast.training_floor(pd.concat([prices_2024, prices_2025]), 0.01)
year = pricecast.rescale_to_level(model.predict(future), level=tyndp_level,
                                  floor=floor, weights=future["load"])
```

The scale is chosen so that the year *after* clipping has the scenario's mean.
Two cautions apply.

- **Scarcity hours lift the mean.** TYNDP's KPI mean includes them: Belgium's
  2040 mean reads 110.6 EUR/MWh with them and 87.4 without, both weighted over
  the weather scenarios. Matched to the higher figure, a model that cannot
  produce scarcity prices lifts every ordinary hour instead. With the hourly
  results at hand, take each weather scenario's load-weighted mean over its
  ordinary hours and weight the scenarios by TYNDP's probabilities.
- **If unsure, choose the low end of the range.** Rescaling multiplies every
  hour, so a level set too high also widens the gap between cheap and dear
  hours. Flexibility then looks more valuable than it is, and the design costs
  more than one sized on a level set too low by the same amount.

### 6. Check how far the model reaches

The model is linear in its drivers. Where solar or wind roughly doubles, many
hours have a net load (load minus solar minus wind) lower than anything in the
training data, and the model keeps lowering the midday price where a real
market stops. Two counts measure how far a year has gone:

```python
beyond = pricecast.share_beyond_training(future, training_drivers)  # % of hours
on_floor = 100.0 * float((year <= floor + 1e-9).mean())            # % of hours
```

where `training_drivers` are the drivers the model was fitted on - the market
years', or TYNDP's own. While both stay at a few percent, use the year; past
that, use the scenario's own hourly prices. A model fitted on market years also
holds storage and demand response at their training level, so read its future
spreads as upper bounds; fitted on the scenario's hourly results, it carries
them. TYNDP's 10% and 90% price quantiles, which the year is not fitted to, give
an independent check.

## Where the inputs come from

| input | source |
|---|---|
| installed solar and wind, annual demand, per country and target year | TYNDP 2026 [KPI dashboard](https://2026-data.entsos-tyndp-scenarios.eu/output/model-results/kpi-dashboards/NT+_KPI_Dashboard.xlsx): NT+ for 2030, 2035, 2040 and 2050; its higher- and lower-growth variants (HEV, LEV) for 2035 and 2040 |
| price level, and the 10% and 90% quantiles to check against | the same KPI dashboard: the rows "Prices [€/MWh]", in the weather-weighted columns |
| hourly prices and drivers to fit on, and a level without scarcity hours | TYNDP 2026 [hourly dashboards](https://2026-data.entsos-tyndp-scenarios.eu/output/model-results/hourly-dashboards/NT+_TimeSeriesDashboard.zip), three weather scenarios per target year, weighted as in the [Methodology Report](https://www.entsog.eu/sites/default/files/2026-06/ENTSOs_TYNDP2026_Scenarios_Methodology_Report_260611.pdf) (Table 36) |
| Spain's rooftop PV, to take out of its target | TYNDP's [PEMMDB capacity inputs](https://2026-data.entsos-tyndp-scenarios.eu/input/model-input/national-trends/PEMMDB_2.X.zip) (National Trends) |
| the weather year's drivers and installed capacity | the ENTSO-E Transparency Platform (`pricecast.entsoe.fetch_year`; installed capacity per production type) |
| other weather years | the Pan-European Climate Database (PECD v4.2, Copernicus), from which TYNDP draws its weather scenarios |

## A year or two ahead

Exchange futures for base-load power give the level of a year or two ahead
directly. `gas_plant_cost` and `level_ratio` remain in the package for a level
built from gas and carbon prices - a gas plant's running cost times a recent
ratio of the mean price to that cost - but only as a near-term tool. After
2030, as gas sets the price in fewer hours, such a level overshoots TYNDP's
prices by a quarter to almost four times.

## Reusing a past year instead

If you do reuse a past price year, lay it on the target year so that both start
at the same local hour (`pricecast.lay_on_calendar`). For Central European
markets a calendar year opens at 23:00 UTC on 31 December. Laid on an index
that starts at 00:00 UTC, every reused hour lands one hour late, which is
enough to misplace every daily peak and trough a storage model trades on.
