import numpy as np
import pandas as pd
import pytest

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


RECIPE_KEYS = {"floor_eur_mwh", "floor_share_pct", "lowest_net_load_mw"}


def test_market_models_record_their_floor_and_reach():
    for country in pricecast.available():
        assert RECIPE_KEYS <= set(pricecast.load(country).metadata)


def test_tyndp_models_ship_for_five_markets_and_four_years():
    assert pricecast.available("TYNDP2026") == [
        (c, y) for c in ["BE", "DE", "ES", "FR", "PL"] for y in (2030, 2035, 2040, 2050)]


def test_every_tyndp_model_predicts_and_carries_the_recipe(synthetic_market):
    _, drivers, _ = synthetic_market
    for country, target in pricecast.available("TYNDP2026"):
        model = pricecast.load(country, scenario="TYNDP2026", year=target)
        meta = model.metadata
        assert (meta["country"], meta["target_year"]) == (country, target)
        assert RECIPE_KEYS | {"level_eur_mwh", "drivers"} <= set(meta)
        assert set(meta["drivers"]) == {"solar_gw", "wind_gw", "demand_twh"}
        year = model.predict(drivers)
        assert np.isfinite(year).all()
        assert year.index.equals(drivers.index)


def test_a_scenario_model_needs_its_scenario_and_year():
    with pytest.raises(ValueError):
        pricecast.load("BE", scenario="TYNDP2026")
    with pytest.raises(ValueError):
        pricecast.load("BE", year=2040)
    with pytest.raises(KeyError):
        pricecast.load("BE", scenario="TYNDP2026", year=2045)
    with pytest.raises(KeyError):
        pricecast.load("BE", scenario="ERAA2025", year=2030)
