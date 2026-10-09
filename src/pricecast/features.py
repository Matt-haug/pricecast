"""The regressors of the price model, built from the clock and three drivers.

The model is one ordinary least-squares regression on hourly day-ahead price:

    p_t = b_0 + sum_h b_h D_{h,t} + sum_d b_d E_{d,t}
          + b_L L_t + b_S S_t + b_W W_t + b_Q max(L_t - S_t - W_t, 0)^2

where p_t is the price (EUR/MWh) in hour t; D_{h,t} is 1 in hour-of-day h
(h = 1..23, hour 0 the reference) and 0 otherwise; E_{d,t} is 1 on weekday d
(d = 0..5, Monday to Saturday, Sunday the reference); L_t, S_t and W_t are load,
solar and wind generation in MW; and the b are the fitted coefficients. The last
term is the *net-load curvature*. Fitted on 2023-24 it was negative in all five
markets of the paper -- the price response flattens as residual demand rises --
but it is small and its sign can change with the window (Germany's 2024-25 fit
is slightly positive), so read it as a curvature, not as a scarcity premium.

Hour and weekday are read in the time zone given by the `timezone` option --
UTC by default, which is how the published coefficients were fitted.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

DRIVERS = ("load", "solar", "wind")

# The specification of the paper: one set of terms for every market.
DEFAULT_FEATURES: dict[str, object] = {
    "hour_dummies": True,
    "weekday_dummies": True,
    "net_load_curvature": True,
    "driver_lags": (),
    "timezone": "UTC",
}


def normalise_features(features: Mapping[str, object] | None) -> dict[str, object]:
    """Fill in defaults and check the option names."""
    out = dict(DEFAULT_FEATURES)
    for key, value in dict(features or {}).items():
        if key not in DEFAULT_FEATURES:
            raise KeyError(f"unknown feature option {key!r}; "
                           f"expected one of {sorted(DEFAULT_FEATURES)}")
        out[key] = value
    out["driver_lags"] = tuple(sorted({int(v) for v in out["driver_lags"] if int(v) > 0}))
    out["timezone"] = str(out["timezone"])
    return out


def design_matrix(index: pd.DatetimeIndex, drivers: pd.DataFrame,
                  features: Mapping[str, object] | None = None
                  ) -> tuple[list[str], np.ndarray]:
    """Column names and the regressor matrix, intercept first.

    `drivers` must hold `load`, `solar` and `wind` on `index`, in MW.
    """
    opts = normalise_features(features)
    clock = index.tz_convert(opts["timezone"]) if index.tz is not None else index
    hour = clock.hour.to_numpy(dtype=int)
    weekday = clock.dayofweek.to_numpy(dtype=int)
    load, solar, wind = (drivers[d].to_numpy(dtype=float) for d in DRIVERS)

    names, columns = ["const"], [np.ones(index.size)]
    if opts["hour_dummies"]:
        for h in range(1, 24):
            names.append(f"hour_{h}")
            columns.append((hour == h).astype(float))
    if opts["weekday_dummies"]:
        for d in range(6):
            names.append(f"dow_{d}")
            columns.append((weekday == d).astype(float))
    for name, values in (("load", load), ("solar", solar), ("wind", wind)):
        names.append(name)
        columns.append(values)
    if opts["net_load_curvature"]:
        names.append("net_load_sq")
        columns.append(np.maximum(load - solar - wind, 0.0) ** 2)
    for lag in opts["driver_lags"]:
        for name, values in (("load", load), ("solar", solar), ("wind", wind)):
            names.append(f"{name}_lag_{lag}")
            columns.append(np.concatenate([np.full(lag, values[0]), values[:-lag]]))
    return names, np.column_stack(columns)
