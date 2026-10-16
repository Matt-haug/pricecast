"""Belgium in 2035 under TYNDP 2026's uncertainty: one price year per sample.

Follows docs/uncertainty.md. Needs `pip install "pricecast[entsoe]" scipy` and
an ENTSO-E token in the ENTSOE_TOKEN environment variable.

Four inputs are sampled, each uniformly over its range (TYNDP 2026, KPI
dashboard; see the uncertainty page for how each range is built):

    solar capacity   15.6 - 29.5 GW    the National Trends+ fleet of 2030 to 2040
    wind capacity     7.8 - 17.6 GW    the same: the build-out five years early or late
    annual demand   122.7 - 145.3 TWh  the lower- to higher-growth variant (LEV to HEV)
    price level      38.0 - 109.3 EUR/MWh  LEV to HEV, load-weighted

Each sample becomes a price year in the 2025 weather; the script reports the
spread of the years' structure. Feed the years to your own design model and fit a
polynomial chaos expansion to its outputs to rank the inputs.
"""

import numpy as np
import pandas as pd
from scipy.stats import qmc

import pricecast
from pricecast.entsoe import fetch_year

(p24, d24), (p25, d25) = fetch_year("BE", 2024), fetch_year("BE", 2025)
model = pricecast.load("BE")                       # fitted on 2024-25
training = pd.concat([d24, d25])
floor = pricecast.training_floor(pd.concat([p24, p25]))

# The 2025 weather year's fleet at mid-year, interpolated towards TYNDP's 2030.
solar_2025 = pricecast.mid_year_capacity(10.70, later=15.64, years_between=5)
wind_2025 = pricecast.mid_year_capacity(5.44, later=7.84, years_between=5)
demand_2025_twh = d25["load"].sum() / 1e6

names = ["solar (GW)", "wind (GW)", "demand (TWh)", "level (EUR/MWh)"]
low, high = [15.6, 7.8, 122.7, 38.0], [29.5, 17.6, 145.3, 109.3]
samples = pd.DataFrame(qmc.scale(qmc.Sobol(d=4, seed=1).random(32), low, high),
                       columns=names)

rows = []
for solar, wind, demand, level in samples.to_numpy():
    future = pricecast.scale_drivers(d25, solar=solar / solar_2025, wind=wind / wind_2025,
                                     load=demand / demand_2025_twh)
    year = pricecast.rescale_to_level(model.predict(future), level, floor=floor,
                                      weights=future["load"])
    rows.append({**pricecast.structure_metrics(year, solar=future["solar"]),
                 "beyond training (%)": pricecast.share_beyond_training(future, training),
                 "on the floor (%)": 100.0 * float((year <= floor + 1e-9).mean())})

outputs = pd.DataFrame(rows)
pd.set_option("display.width", 160)
print(f"{len(samples)} price years for Belgium in 2035\n")
print(outputs.quantile([0.05, 0.5, 0.95]).T.round(2)
      .rename(columns={0.05: "P05", 0.5: "median", 0.95: "P95"}))
