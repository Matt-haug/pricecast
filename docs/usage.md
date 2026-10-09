# Usage

## Data in

Everything takes pandas objects on an hourly `DatetimeIndex` (UTC, or
time-zone-naive and read as UTC):

- **prices**: a `Series` of day-ahead prices, EUR/MWh;
- **drivers**: a `DataFrame` (or a dict of `Series`) with columns `load`,
  `solar` and `wind`, in MW. Wind is onshore plus offshore.

`pricecast.entsoe.fetch_year(country, year)` returns both for one calendar year,
downloaded from the ENTSO-E Transparency Platform. It needs the optional
dependency and a free API token (as `token=` or the `ENTSOE_TOKEN` environment
variable):

```bash
pip install "pricecast[entsoe]"
```

### Getting a token

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
