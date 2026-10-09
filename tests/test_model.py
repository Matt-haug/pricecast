import numpy as np
import pandas as pd
import pytest

import pricecast


def test_fit_recovers_known_coefficients(synthetic_market):
    prices, drivers, truth = synthetic_market
    model = pricecast.fit(prices, drivers)
    for name in ("load", "solar", "wind"):
        assert model.coefficients[name] == pytest.approx(truth[name], rel=0.05)
    assert model.coefficients["hour_19"] == pytest.approx(5.0, abs=0.5)
    assert model.residual_std == pytest.approx(3.0, rel=0.1)


def test_fit_on_several_years_equals_fit_on_their_concatenation(synthetic_market):
    prices, drivers, _ = synthetic_market
    n = len(prices) // 2
    parts = pricecast.fit([prices.iloc[:n], prices.iloc[n:]],
                          [drivers.iloc[:n], drivers.iloc[n:]])
    whole = pricecast.fit(prices, drivers)
    for name, value in whole.coefficients.items():
        assert parts.coefficients[name] == pytest.approx(value, rel=1e-6, abs=1e-9)


def test_prediction_is_the_regression(synthetic_market):
    prices, drivers, _ = synthetic_market
    model = pricecast.fit(prices, drivers)
    names, x = pricecast.design_matrix(prices.index, drivers)
    beta = np.array([model.coefficients[n] for n in names])
    assert np.allclose(model.predict(drivers).to_numpy(), x @ beta)


def test_json_round_trip(tmp_path, synthetic_market):
    prices, drivers, _ = synthetic_market
    model = pricecast.fit(prices, drivers, features={"driver_lags": (1,)},
                          metadata={"country": "XX"})
    path = tmp_path / "model.json"
    model.to_json(path)
    again = pricecast.PriceModel.from_json(path)
    assert again.coefficients == model.coefficients
    assert again.metadata == {"country": "XX"}
    pd.testing.assert_series_equal(again.predict(drivers), model.predict(drivers))


def test_noise_is_reproducible_and_has_the_residual_spread(synthetic_market):
    prices, drivers, _ = synthetic_market
    model = pricecast.fit(prices, drivers)
    a = model.predict(drivers, noise=True, seed=7)
    b = model.predict(drivers, noise=True, seed=7)
    pd.testing.assert_series_equal(a, b)
    noise = a - model.predict(drivers)
    assert noise.std() == pytest.approx(model.residual_std, rel=0.01)


def test_unknown_feature_option_is_refused(synthetic_market):
    prices, drivers, _ = synthetic_market
    with pytest.raises(KeyError):
        pricecast.fit(prices, drivers, features={"month_dummies": True})


def test_missing_driver_is_refused(synthetic_market):
    prices, drivers, _ = synthetic_market
    with pytest.raises(KeyError):
        pricecast.fit(prices, drivers.drop(columns="wind"))
