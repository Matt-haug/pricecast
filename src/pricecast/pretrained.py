"""Models fitted on recent years, shipped with the package.

Each was fitted on the two most recent complete years of ENTSO-E Transparency
Platform data (day-ahead price, actual total load, actual solar and wind
generation) for one bidding zone. They are a starting point: refit on your own
window when it matters, and set the level from outside either way.
"""

from __future__ import annotations

import json
from importlib import resources

from .model import PriceModel


def available() -> list[str]:
    """Country codes with a shipped model."""
    files = resources.files("pricecast.data")
    return sorted(p.name[:-5] for p in files.iterdir() if p.name.endswith(".json"))


def load(country: str) -> PriceModel:
    """The shipped model for `country` (e.g. "BE", "DE", "FR", "ES", "PL")."""
    name = f"{country.upper()}.json"
    files = resources.files("pricecast.data")
    path = files.joinpath(name)
    if not path.is_file():
        raise KeyError(f"no shipped model for {country!r}; have {available()}")
    return PriceModel.from_dict(json.loads(path.read_text(encoding="utf-8")))
