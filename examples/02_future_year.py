"""A 2030 price year for Belgium from TYNDP 2026, following docs/recipe.md.

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
# ENTSO-E installed capacity at the start of 2025 (GW), and TYNDP 2026 (National
# Trends+, KPI dashboard) for 2030: solar and wind capacity, and demand as native
# and fixed demand plus electric-vehicle charging.
solar_2030, wind_2030, demand_2030_twh = 15.64, 7.84, 110.7
solar_2025 = pricecast.mid_year_capacity(10.70, later=solar_2030, years_between=5)
wind_2025 = pricecast.mid_year_capacity(5.44, later=wind_2030, years_between=5)
demand_2025_twh = d25["load"].sum() / 1e6

future = pricecast.scale_drivers(d25, solar=solar_2030 / solar_2025,
                                 wind=wind_2030 / wind_2025,
                                 load=demand_2030_twh / demand_2025_twh)

# --- 4. run the model ------------------------------------------------------------
shape = model.predict(future)

# --- 5. floor the year and give it TYNDP's level -----------------------------------
# TYNDP 2026 NT+ 2030, KPI dashboard: Belgium's load-weighted mean price, weighted
# over the three weather scenarios, 65.1 EUR/MWh; its 10% and 90% quantiles,
# 15.6 and 105.9 EUR/MWh, are kept for the check below.
level, tyndp_q10, tyndp_q90 = 65.1, 15.6, 105.9
floor = pricecast.training_floor(pd.concat([p24, p25]))
year_2030 = pricecast.rescale_to_level(shape, level, floor=floor, weights=future["load"])

# --- 6. how far does the model reach? ---------------------------------------------
beyond = pricecast.share_beyond_training(future, pd.concat([d24, d25]))
on_floor = 100.0 * float((year_2030 <= floor + 1e-9).mean())

print(f"2030 level = {level:.1f} EUR/MWh (load-weighted), floor = {floor:.1f} EUR/MWh")
print(f"hours beyond the training net load: {beyond:.1f}%, on the floor: {on_floor:.1f}%")
print(f"10% / 90% quantiles: model {year_2030.quantile(0.1):.1f} / "
      f"{year_2030.quantile(0.9):.1f}, TYNDP {tyndp_q10:.1f} / {tyndp_q90:.1f} EUR/MWh")
# Each year weighted by its own solar output: 2025's real fleet, 2030's scaled one.
pd.set_option("display.width", 160)
print(pd.DataFrame({
    "actual 2025": pricecast.structure_metrics(p25, solar=d25["solar"]),
    "2030": pricecast.structure_metrics(year_2030, solar=future["solar"]),
}).round(2))
