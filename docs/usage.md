# Usage

## Data in

Everything takes pandas objects on an hourly `DatetimeIndex` (UTC, or
time-zone-naive and read as UTC):

- **prices**: a `Series` of day-ahead prices, EUR/MWh;
- **drivers**: a `DataFrame` (or a dict of `Series`) with columns `load`,
  `solar` and `wind`, in MW. Wind is onshore plus offshore.

`pricecast.entsoe.fetch_year(country, year)` returns both for one calendar year,
downloaded from the ENTSO-E Transparency Platform.

## Fit, or start from a shipped model

```python
import pricecast

model = pricecast.fit([prices_2024, prices_2025], [drivers_2024, drivers_2025],
                      metadata={"country": "BE"})
model.to_json("be_2024_2025.json")

model = pricecast.load("BE")          # shipped: BE, DE, FR, ES, PL, fitted on 2024-25
pricecast.available()
```

## Generate

```python
year = model.predict(drivers)                       # the conditional mean
noisy = model.predict(drivers, noise=True, seed=1)  # with the residual process
```

## Check the structure

```python
pricecast.structure_metrics(year, solar=drivers["solar"], heat=my_heat_demand)
pricecast.compare({"actual": prices_2025, "model": year}, truth="actual",
                  solar=drivers["solar"])
```

Reports the mean, the share of negative hours, the midday price over the mean,
the evening-minus-midday price, the solar value factor, the daily four-hour
spread and the heat-weighted price over the mean.

## A future year

See [the recipe](recipe.md) and `examples/02_future_year.py`.

```python
future = pricecast.scale_drivers(drivers_2025, solar=1.39, wind=1.38, load=1.30)
k = pricecast.level_ratio(prices_2025.mean(), gas_eur_mwh=36.1, co2_eur_t=73.4)
level = k * pricecast.gas_plant_cost(34.6, 97.5)
year = pricecast.rescale_to_level(model.predict(future), level)
print(pricecast.share_beyond_training(future, training_drivers))
```
