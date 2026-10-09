"""Fit on two years, generate the next, and compare it with what happened.

Needs `pip install "pricecast[entsoe]"` and an ENTSO-E token in the
ENTSOE_TOKEN environment variable.
"""

import pandas as pd

import pricecast
from pricecast.entsoe import fetch_year

COUNTRY = "BE"

# Two years to fit on, one to check against.
data = {year: fetch_year(COUNTRY, year) for year in (2023, 2024, 2025)}
model = pricecast.fit([data[2023][0], data[2024][0]], [data[2023][1], data[2024][1]],
                      metadata={"country": COUNTRY, "train_years": [2023, 2024]})

actual, drivers = data[2025]
generated = model.predict(drivers, index=actual.index)

# The level is not the model's job: rescale to the year's real mean to compare
# shapes only, as a study would after taking the level from a scenario.
shaped = pricecast.rescale_to_level(generated, actual.mean())

pd.set_option("display.width", 160)
print(pricecast.compare({"actual 2025": actual, "model": generated,
                         "model, level given": shaped},
                        truth="actual 2025", solar=drivers["solar"]).round(2).T)
