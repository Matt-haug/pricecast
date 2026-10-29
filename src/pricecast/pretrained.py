"""Models shipped with the package: market years, and a scenario's hourly results.

The market models were each fitted on the two most recent complete years of
ENTSO-E Transparency Platform data (day-ahead price, actual total load, actual
solar and wind generation) for one bidding zone. They are a starting point:
refit on your own window when it matters, and set the level from outside either
way.

The scenario models were each fitted on ENTSO-E's TYNDP 2026 hourly results
for one country and target year (2030, 2035, 2040, 2050): its central scenario
(National Trends+) under its three representative weather scenarios, scarcity
hours above 1000 EUR/MWh left out. They carry the scenario's storage, demand
response, interconnection and marginal-cost structure, and their metadata
carries what the recipe needs without TYNDP's data: the scenario's fleet and
demand (`drivers`), its level over ordinary hours (`level_eur_mwh`), the floor
(`floor_eur_mwh`) and the lowest net load fitted on (`lowest_net_load_mw`).
Every shipped model, market or scenario, records the last three.
"""

from __future__ import annotations

import json
from importlib import resources

from .model import PriceModel

# Scenario name -> folder under pricecast/data.
SCENARIOS = {"TYNDP2026": "tyndp2026"}


def _scenario_folder(scenario: str):
    key = scenario.upper().replace(" ", "").replace("-", "")
    if key not in SCENARIOS:
        raise KeyError(f"no shipped scenario {scenario!r}; have {sorted(SCENARIOS)}")
    return resources.files("pricecast.data").joinpath(SCENARIOS[key])


def available(scenario: str | None = None) -> list:
    """What `load` can open.

    Without `scenario`, the country codes with a shipped market model. With
    `scenario="TYNDP2026"`, the (country, target year) pairs with a model fitted
    on that scenario's hourly results.
    """
    if scenario is None:
        files = resources.files("pricecast.data")
        return sorted(p.name[:-5] for p in files.iterdir() if p.name.endswith(".json"))
    pairs = []
    for p in _scenario_folder(scenario).iterdir():
        if p.name.endswith(".json"):
            country, year = p.name[:-5].split("_")
            pairs.append((country, int(year)))
    return sorted(pairs)


def load(country: str, scenario: str | None = None, year: int | None = None) -> PriceModel:
    """A shipped model.

    `load("BE")` is Belgium's model fitted on the market years 2024-2025.
    `load("BE", scenario="TYNDP2026", year=2040)` is the one fitted on TYNDP
    2026's hourly results for 2040; its `metadata` holds the scenario's
    drivers and level besides the floor and lowest training net load.
    """
    if scenario is None:
        if year is not None:
            raise ValueError("a year selects a scenario model; give scenario= as well")
        path = resources.files("pricecast.data").joinpath(f"{country.upper()}.json")
        if not path.is_file():
            raise KeyError(f"no shipped model for {country!r}; have {available()}")
    else:
        if year is None:
            raise ValueError(f"give the target year; have {available(scenario)}")
        path = _scenario_folder(scenario).joinpath(f"{country.upper()}_{int(year)}.json")
        if not path.is_file():
            raise KeyError(f"no shipped {scenario} model for {country!r} in {year}; "
                           f"have {available(scenario)}")
    return PriceModel.from_dict(json.loads(path.read_text(encoding="utf-8")))
