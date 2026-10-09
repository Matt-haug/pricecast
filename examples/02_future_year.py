"""A 2030 price year for Belgium, following the recipe in docs/recipe.md.

Needs `pip install "pricecast[entsoe]"` and an ENTSO-E token in the
ENTSOE_TOKEN environment variable.
Every scenario number below is quoted with its source; replace them with your
own scenario.
"""

import pandas as pd

import pricecast
from pricecast.entsoe import fetch_year

# --- 1. fit on the two most recent complete years -------------------------------
(p24, d24), (p25, d25) = fetch_year("BE", 2024), fetch_year("BE", 2025)
model = pricecast.fit([p24, p25], [d24, d25])

# --- 2. one weather year: 2025, for the drivers and for anything else weather-driven

# --- 3. scale the drivers ---------------------------------------------------------
# ENTSO-E installed capacity at the start of 2025 (GW), and ERAA 2025 (National
# Trends, final data, dashboard raw data) for 2028 and 2030.
solar_2025 = pricecast.mid_year_capacity(10.70, later=13.85, years_between=3)
wind_2025 = pricecast.mid_year_capacity(5.44, later=6.98, years_between=3)
solar_2030, wind_2030, demand_2030_twh = 15.64, 7.84, 104.5
demand_2025_twh = d25["load"].sum() / 1e6

future = pricecast.scale_drivers(d25, solar=solar_2030 / solar_2025,
                                 wind=wind_2030 / wind_2025,
                                 load=demand_2030_twh / demand_2025_twh)

# --- 4. run the model ------------------------------------------------------------
shape = model.predict(future)

# --- 5. the level: Belgium's 2025 ratio times a 2030 gas plant's running cost ----
# 2025: World Bank "Natural gas, Europe" at the ECB annual rate (36.1 EUR/MWh)
# and the volume-weighted EEX auction price of EU allowances (73.4 EUR/t).
k = pricecast.level_ratio(p25.mean(), gas_eur_mwh=36.1, co2_eur_t=73.4)
# 2030: ERAA 2025 gas 9.615 EUR/GJ and CO2 97.47 EUR/t (2024 EUR).
level = k * pricecast.gas_plant_cost(9.615 * 3.6, 97.47)

# --- 6. how far is the model extrapolating? ---------------------------------------
training = pd.concat([d24, d25])
share = pricecast.share_beyond_training(future, training)
floor = pricecast.training_floor(pd.concat([p24, p25])) if share > 1.0 else None
year_2030 = pricecast.rescale_to_level(shape, level, floor=floor)

print(f"ratio k = {k:.2f}, 2030 level = {level:.1f} EUR/MWh")
print(f"hours beyond the training net load: {share:.1f}%"
      + (f" -> floored at {floor:.1f} EUR/MWh" if floor is not None else ""))
# Each year weighted by its own solar output: 2025's real fleet, 2030's scaled one.
pd.set_option("display.width", 160)
print(pd.DataFrame({
    "actual 2025": pricecast.structure_metrics(p25, solar=d25["solar"]),
    "2030": pricecast.structure_metrics(year_2030, solar=future["solar"]),
}).round(2))
