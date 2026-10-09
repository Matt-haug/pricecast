# Changelog

Notable changes to `pricecast`. This project follows
[semantic versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-09

First version, extracted from the research code behind the accompanying paper.

### Added
- The price model: one least-squares regression of hourly day-ahead price on
  hour and weekday dummies, load, solar and wind generation and a net-load
  curvature term (`fit`, `PriceModel.predict`), with an optional smoothed
  Student-t residual process.
- Models for BE, DE, FR, ES and PL fitted on 2024-2025 (`load`, `available`).
- The future-year recipe: `scale_drivers`, `mid_year_capacity`,
  `gas_plant_cost`, `level_ratio`, `rescale_to_level` (with an optional floor and load weighting),
  `share_beyond_training` and `training_floor`.
- Structure metrics of a price year (`structure_metrics`, `compare`) and
  `lay_on_calendar` for reusing a past year without shifting its hours.
- Optional ENTSO-E download of a year of prices and drivers
  (`pricecast.entsoe.fetch_year`).
