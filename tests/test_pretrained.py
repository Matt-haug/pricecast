import numpy as np
import pandas as pd

import pricecast


def test_five_markets_ship():
    assert pricecast.available() == ["BE", "DE", "ES", "FR", "PL"]


def test_every_shipped_model_predicts_a_plausible_year(synthetic_market):
    _, drivers, _ = synthetic_market
    for country in pricecast.available():
        model = pricecast.load(country)
        assert model.metadata["train_years"] == [2024, 2025]
        year = model.predict(drivers)
        assert np.isfinite(year).all()
        assert year.index.equals(drivers.index)


def test_shipped_solar_coefficients_are_negative():
    for country in pricecast.available():
        assert pricecast.load(country).coefficients["solar"] < 0.0


def test_unknown_country_is_refused():
    try:
        pricecast.load("XX")
    except KeyError:
        return
    raise AssertionError("expected a KeyError")
