"""A 2040 price year for Belgium from the model fitted on TYNDP 2026's hourly results.

The recipe of docs/recipe.md with a shipped scenario model instead of one fitted
on market years: the coefficients, the level, the floor and the reach bound all
come from TYNDP 2026 (National Trends+, three weather scenarios), so only the
weather year's drivers are downloaded. Needs `pip install "pricecast[entsoe]"`
and an ENTSO-E token in the ENTSOE_TOKEN environment variable.
"""

import pandas as pd

import pricecast
from pricecast.entsoe import fetch_year

# --- 1. the model fitted on TYNDP's 2040 results ----------------------------------
model = pricecast.load("BE", scenario="TYNDP2026", year=2040)
target = model.metadata
bridge = pricecast.load("BE", scenario="TYNDP2026", year=2030).metadata["drivers"]

# --- 2. one weather year: 2025 ------------------------------------------------------
p25, d25 = fetch_year("BE", 2025)

# --- 3. scale the drivers to TYNDP's 2040 fleet and demand ---------------------------
# ENTSO-E installed capacity at the start of 2025 (GW), brought to mid-year
# towards TYNDP's 2030 fleet.
solar_2025 = pricecast.mid_year_capacity(10.70, later=bridge["solar_gw"], years_between=5)
wind_2025 = pricecast.mid_year_capacity(5.44, later=bridge["wind_gw"], years_between=5)
demand_2025_twh = d25["load"].sum() / 1e6
drivers = target["drivers"]
future = pricecast.scale_drivers(d25, solar=drivers["solar_gw"] / solar_2025,
                                 wind=drivers["wind_gw"] / wind_2025,
                                 load=drivers["demand_twh"] / demand_2025_twh)

# --- 4 and 5. run the model, floor the year and give it TYNDP's level ----------------
# The level is TYNDP's load-weighted mean over its ordinary hours, scarcity hours
# out; the floor is the 1% quantile of the hours the model was fitted on.
floor = target["floor_eur_mwh"]
year_2040 = pricecast.rescale_to_level(model.predict(future), target["level_eur_mwh"],
                                       floor=floor, weights=future["load"])

# --- 6. how far does the model reach? -----------------------------------------------
# TYNDP clears many hours at its floor, so compare the hours on the floor with the
# share the training hours themselves put there.
beyond = pricecast.share_beyond_training(future, target["lowest_net_load_mw"])
on_floor = 100.0 * float((year_2040 <= floor + 1e-9).mean())

print(f"2040 level = {target['level_eur_mwh']:.1f} EUR/MWh (KPI mean with scarcity "
      f"hours {target['kpi_level_eur_mwh']:.1f}), floor = {floor:.1f} EUR/MWh")
print(f"hours beyond the training net load: {beyond:.1f}%; on the floor: {on_floor:.1f}% "
      f"(training hours: {target['floor_share_pct']:.1f}%)")
print(f"10% / 90% quantiles: model {year_2040.quantile(0.1):.1f} / "
      f"{year_2040.quantile(0.9):.1f}, TYNDP {target['kpi_price_q10_eur_mwh']:.1f} / "
      f"{target['kpi_price_q90_eur_mwh']:.1f} EUR/MWh")
pd.set_option("display.width", 160)
print(pd.DataFrame({
    "actual 2025": pricecast.structure_metrics(p25, solar=d25["solar"]),
    "2040": pricecast.structure_metrics(year_2040, solar=future["solar"]),
}).round(2))
