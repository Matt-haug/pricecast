import numpy as np
import pandas as pd
import pytest

import pricecast


def test_gas_plant_cost_of_the_eraa_2030_prices():
    # ERAA 2025: gas 9.615 EUR/GJ = 34.6 EUR/MWh, CO2 97.47 EUR/t
    assert pricecast.gas_plant_cost(9.615 * 3.6, 97.47) == pytest.approx(98.74, abs=0.01)


def test_level_ratio_inverts_the_cost():
    assert pricecast.level_ratio(80.0, 35.0, 75.0) * pricecast.gas_plant_cost(35.0, 75.0) \
        == pytest.approx(80.0)


def test_mid_year_capacity_is_a_sixth_of_the_way_to_a_figure_three_years_on():
    assert pricecast.mid_year_capacity(90.0, 150.0, 3) == pytest.approx(100.0)


def test_rescale_to_level_hits_the_level_without_a_floor():
    s = pd.Series([10.0, 50.0, 90.0, -20.0])
    assert pricecast.rescale_to_level(s, 60.0).mean() == pytest.approx(60.0)


def test_rescale_to_level_hits_the_level_with_a_floor_and_respects_it():
    s = pd.Series(np.linspace(-100.0, 200.0, 301))
    out = pricecast.rescale_to_level(s, 80.0, floor=-10.0)
    assert out.mean() == pytest.approx(80.0, abs=1e-6)
    assert out.min() >= -10.0


def test_rescale_refuses_a_floor_above_the_level():
    with pytest.raises(ValueError):
        pricecast.rescale_to_level(pd.Series([1.0, 2.0]), 5.0, floor=10.0)


def test_scale_drivers_scales_each_column(synthetic_market):
    _, drivers, _ = synthetic_market
    out = pricecast.scale_drivers(drivers, solar=2.0, wind=1.5, load=1.1)
    assert np.allclose(out["solar"], 2.0 * drivers["solar"])
    assert np.allclose(out["wind"], 1.5 * drivers["wind"])
    assert np.allclose(out["load"], 1.1 * drivers["load"])


def test_share_beyond_training_grows_with_solar(synthetic_market):
    _, drivers, _ = synthetic_market
    assert pricecast.share_beyond_training(drivers, drivers) == 0.0
    more = pricecast.scale_drivers(drivers, solar=3.0)
    assert pricecast.share_beyond_training(more, drivers) > 1.0


def test_training_floor_is_the_low_quantile():
    s = pd.Series(np.arange(101.0), index=pd.date_range("2025-01-01", periods=101,
                                                         freq="h", tz="UTC"))
    assert pricecast.training_floor(s, 0.01) == pytest.approx(1.0)


def test_rescale_to_level_matches_a_load_weighted_mean():
    index = pd.date_range("2025-01-01", periods=4, freq="h", tz="UTC")
    s = pd.Series([10.0, 20.0, 30.0, 40.0], index=index)
    load = pd.Series([1.0, 1.0, 1.0, 3.0], index=index)
    out = pricecast.rescale_to_level(s, 50.0, weights=load)
    assert np.average(out, weights=load) == pytest.approx(50.0)
    floored = pricecast.rescale_to_level(s - 25.0, 50.0, floor=0.0, weights=load)
    assert np.average(floored, weights=load) == pytest.approx(50.0)
    assert floored.min() >= 0.0
