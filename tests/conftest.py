import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_market():
    """Two years of drivers and a price built from known coefficients."""
    index = pd.date_range("2023-01-01", "2025-01-01", freq="h", tz="UTC", inclusive="left")
    rng = np.random.default_rng(1)
    hour = index.hour.to_numpy()
    day = index.dayofyear.to_numpy()
    load = 9000 + 1500 * np.sin(2 * np.pi * (hour - 6) / 24) + 800 * np.cos(2 * np.pi * day / 365)
    solar = np.clip(np.sin(np.pi * (hour - 6) / 12), 0, None) * (3000 + 2000 * np.sin(2 * np.pi * (day - 80) / 365))
    wind = 1500 + 900 * rng.standard_normal(index.size).cumsum() / np.sqrt(index.size) + 400 * rng.random(index.size)
    wind = np.clip(wind, 0, None)
    drivers = pd.DataFrame({"load": load, "solar": solar, "wind": wind}, index=index)
    truth = {"const": 20.0, "load": 0.008, "solar": -0.012, "wind": -0.006,
             "net_load_sq": -1.0e-7}
    net = np.maximum(load - solar - wind, 0.0)
    price = (truth["const"] + truth["load"] * load + truth["solar"] * solar
             + truth["wind"] * wind + truth["net_load_sq"] * net ** 2
             + 5.0 * (index.hour == 19) + rng.normal(0, 3.0, index.size))
    return pd.Series(price, index=index), drivers, truth
