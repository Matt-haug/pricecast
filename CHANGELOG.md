# Changelog

Notable changes to `pricecast`. This project follows
[semantic versioning](https://semver.org/).

## [Unreleased]

### Added
- The documentation shows what the model does in ten figures: on the home
  page, the drivers and prices of 2025's median week, then its best and worst
  weeks with their drivers; the conditional mean, the noise and the year's
  structure on the usage page; a 2030 year from TYNDP, its level, its reach
  and a reused past year in the recipe; a solar sweep and 32 sampled years on
  the page on uncertainty. Each caption opens with the figure's message.
  `examples/build_doc_figures.py` draws them from ENTSO-E's Belgian market
  years, in the house style of `examples/figure_style.py`, which the sister
  package `loadcast` shares: after Jean-luc Doumont's *Trees, maps, and
  theorems*, lines named on the plot, axes apart from the data, solid lines
  told apart by colour, and Manrope when it is installed or its files sit in
  the folder `PRICECAST_FIGURE_FONTS` names.
- The mathematics page credits the time-series theory it builds on (Box,
  Jenkins, Reinsel and Ljung, *Time Series Analysis*): the package adds no new
  theory, only a way of combining it to produce the signals a user asks for.
- The README and the documentation's home page point to the sister project
  `loadcast`, by the same authors, for hourly industrial heat, cold and
  electricity demand.

### Fixed
- The documentation build pins `pymdown-extensions` below 11: with 12.x,
  mkdocstrings fails on every page that renders a docstring.

## [0.1.5] - 2026-10-16

### Changed
- The documentation presents the package as a parametric price model, for
  scenario sweeps, uncertainty propagation and future years built from a
  market-model scenario. Future years now come from ENTSO-E's TYNDP 2026
  throughout: fleet, demand and load-weighted price level from its KPI
  dashboard, and, where its hourly results are at hand, the coefficients fitted
  on them, with scarcity hours left out of the fit and of the level.
- `examples/02_future_year.py` builds Belgium's 2030 year from TYNDP 2026
  instead of ERAA 2025 and a gas-plant level, and checks it against TYNDP's 10%
  and 90% price quantiles.
- The recipe always floors the year before matching the level, and reports a
  second reach count: the share of hours left on the floor.
- `gas_plant_cost` and `level_ratio` are documented as a near-term tool only;
  their behaviour is unchanged.

### Added
- A documentation page on sweeps and uncertainty propagation: one driver at a
  time, sampled scenario inputs, and polynomial chaos expansions with their
  leave-one-out check.
- `examples/03_uncertainty.py`: 32 price years for Belgium in 2035, sampled over
  TYNDP 2026's build-out timing, demand and price-level ranges.

## [0.1.4] - 2026-10-09

### Fixed
- PyPI listed the co-authors as the authors and the first author only as
  an email; all three are now authors, with a maintainer contact.
- The first author's name is spelled Mattéo, as in `CITATION.cff` and ORCID.

## [0.1.3] - 2026-10-09

### Added
- A logo: the duck curve - a day of electricity prices with an eye - on the
  README, the documentation and the social preview (`docs/assets/`).
- An API reference page in the documentation, generated from the docstrings.

### Changed
- The documentation is restyled to match the logo: Manrope for text, IBM Plex
  Mono for code and titles, the package colour in moderation, a dark mode.
- The PyPI page links the documentation.

## [0.1.2] - 2026-10-09

### Added
- How to get an ENTSO-E token, in the README, the usage page and the
  missing-token error.

### Changed
- The version now comes from the git tag of each release (setuptools-scm).
- The README and documentation are a user guide: what the package is for and
  how to use it, installed from PyPI.
- Ward De Paepe and Francesco Contino added as authors.

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
