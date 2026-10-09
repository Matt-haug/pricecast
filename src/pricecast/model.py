"""Fit the model, keep it, and generate price years from it."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence, Union

import numpy as np
import pandas as pd

from .features import DRIVERS, design_matrix, normalise_features

DriverInput = Union[pd.DataFrame, Mapping[str, pd.Series]]


# =============================================================================
# Input handling
# =============================================================================


def as_utc(series: pd.Series) -> pd.Series:
    """Sorted, de-duplicated, numeric, on a UTC index."""
    if not isinstance(series.index, pd.DatetimeIndex):
        raise TypeError("prices and drivers need a DatetimeIndex")
    out = series.sort_index().astype(float)
    out.index = (out.index.tz_localize("UTC") if out.index.tz is None
                 else out.index.tz_convert("UTC"))
    return out[~out.index.duplicated(keep="first")]


def align_drivers(drivers: DriverInput, index: pd.DatetimeIndex) -> pd.DataFrame:
    """Load, solar and wind on `index`, interpolated in time where an hour is missing."""
    missing = [d for d in DRIVERS if d not in drivers]
    if missing:
        raise KeyError(f"drivers need columns {DRIVERS}; missing {missing}")
    out = {}
    for name in DRIVERS:
        series = as_utc(pd.Series(drivers[name]))
        aligned = series.reindex(index).interpolate(method="time").ffill().bfill()
        out[name] = aligned.fillna(0.0)
    return pd.DataFrame(out, index=index)


# =============================================================================
# The residual process
# =============================================================================


def _student_df(residuals: np.ndarray) -> float:
    """Degrees of freedom of a Student-t with the residuals' excess kurtosis."""
    x = residuals - residuals.mean()
    var = float(np.mean(x ** 2))
    if x.size < 20 or var <= 0.0:
        return 7.0
    excess = float(np.mean(x ** 4)) / var ** 2 - 3.0
    if excess <= 0.2:
        return 30.0
    return float(np.clip(4.0 + 6.0 / excess, 4.2, 60.0))


def residual_noise(n: int, std: float, df: float, seed: int | None = None,
                   window_hours: int = 24) -> np.ndarray:
    """Smoothed Student-t noise with the residuals' spread and tail weight.

    Unit-variance Student-t draws are averaged over a 24-hour window, which
    gives them the day-scale persistence of the real residual, and rescaled to
    the fitted residual standard deviation. The noisy hours are uncorrelated
    with the real ones: right for revenue estimates, wrong for sizing.
    """
    rng = np.random.default_rng(seed)
    nu = max(df, 2.1)
    raw = rng.standard_t(df=nu, size=n) / np.sqrt(nu / (nu - 2.0))
    window = int(max(1, min(window_hours, n)))
    smooth = np.convolve(raw, np.ones(window) / window, mode="same") if window > 1 else raw
    spread = float(np.std(smooth))
    return std * (smooth / spread if spread > 0 else smooth)


# =============================================================================
# The model
# =============================================================================


@dataclass(frozen=True)
class PriceModel:
    """A fitted price model.

    `coefficients` maps each regressor name to its coefficient (EUR/MWh per
    unit of the regressor; the intercept is `const`). `residual_std` and
    `student_df` describe the residual process used when noise is switched on.
    `metadata` records where the model came from.
    """

    coefficients: dict[str, float]
    residual_std: float
    student_df: float
    features: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def predict(self, drivers: DriverInput, index: pd.DatetimeIndex | None = None,
                noise: bool = False, seed: int | None = None) -> pd.Series:
        """The model's price on the given drivers, EUR/MWh.

        `index` defaults to the drivers' own hours. `noise=True` adds the
        residual process; leave it off for sizing.
        """
        if index is None:
            index = as_utc(pd.Series(drivers["load"])).index
        index = pd.DatetimeIndex(index)
        index = index.tz_localize("UTC") if index.tz is None else index.tz_convert("UTC")
        names, x = design_matrix(index, align_drivers(drivers, index), self.features)
        unknown = [n for n in self.coefficients if n not in names]
        if unknown:
            raise ValueError(f"the model has coefficients the features do not build: {unknown}")
        beta = np.array([self.coefficients.get(n, 0.0) for n in names])
        price = x @ beta
        if noise:
            price = price + residual_noise(index.size, self.residual_std,
                                           self.student_df, seed)
        return pd.Series(price, index=index, name="price_eur_mwh")

    # -- persistence ---------------------------------------------------------
    def to_dict(self) -> dict[str, object]:
        features = dict(self.features)
        features["driver_lags"] = list(features.get("driver_lags", ()))
        return {"coefficients": self.coefficients, "residual_std": self.residual_std,
                "student_df": self.student_df, "features": features,
                "metadata": self.metadata}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "PriceModel":
        return cls(coefficients={k: float(v) for k, v in dict(data["coefficients"]).items()},
                   residual_std=float(data["residual_std"]),
                   student_df=float(data["student_df"]),
                   features=normalise_features(data.get("features")),
                   metadata=dict(data.get("metadata", {})))

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> "PriceModel":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def fit(prices: pd.Series | Sequence[pd.Series], drivers: DriverInput | Sequence[DriverInput],
        features: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None) -> PriceModel:
    """Fit the model by least squares on one or several years.

    `prices` is an hourly day-ahead price series (EUR/MWh), or a list of them;
    `drivers` holds `load`, `solar` and `wind` (MW) for the same hours, or a
    list in the same order. Fit on the two or three most recent complete years.
    """
    price_list = list(prices) if isinstance(prices, (list, tuple)) else [prices]
    driver_list = list(drivers) if isinstance(drivers, (list, tuple)) else [drivers]
    if len(price_list) != len(driver_list):
        raise ValueError("give one driver set per price series")
    opts = normalise_features(features)
    names, xs, ys = None, [], []
    for price, driver in zip(price_list, driver_list):
        y = as_utc(price).dropna()
        names, x = design_matrix(y.index, align_drivers(driver, y.index), opts)
        xs.append(x)
        ys.append(y.to_numpy())
    x, y = np.vstack(xs), np.concatenate(ys)
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ beta
    std = max(float(np.std(residuals)), 1e-6)
    return PriceModel(coefficients=dict(zip(names, map(float, beta))),
                      residual_std=std, student_df=_student_df(residuals / std),
                      features=opts, metadata=dict(metadata or {}))
