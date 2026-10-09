# Contributing

Contributions are welcome - issues, questions and pull requests alike.

## Support and scope

**Maintenance.** `pricecast` is maintained by one person alongside doctoral
research. Issues are usually answered within a week or two; there is no
service-level guarantee, and quiet periods around deadlines are normal. If
something is urgent, say so in the issue and it will be triaged sooner.

**Decisions.** The maintainer makes the final call on scope and design. The
reasoning behind a decision is written down in the issue rather than left
implicit, so a disagreement is about something readable.

**What belongs here.** The package generates the *shape* of an hourly
day-ahead price year from physical drivers, and provides the tools to set its
level and to build a future year. Three things are deliberately out of scope,
and a pull request adding them will be declined with this paragraph rather than
silence:

- **Forecasting.** No next-day or next-week price forecasts, and no models whose
  inputs are only known in hindsight.
- **Forecasting the level.** The price level comes from an outside
  fuel-and-carbon scenario. Tools to *apply* one belong here; a model that
  extrapolates the level from price history does not.
- **Dispatch or sizing models.** The package produces prices; what you design
  with them is your study.

## Reporting something

Open an issue with the version (`pricecast.__version__`), the market and years,
and what you expected instead. A five-line reproduction is worth more than a
description.

Reports that a generated year disagrees with a market you know - its midday
trough, its negative hours, its evening peak - are **especially welcome**: five
markets is a small sample, and that is the package's main limitation.

## Making a change

```bash
git clone https://github.com/Matt-haug/pricecast
cd pricecast
python -m pip install -e ".[dev]"
python -m pytest
```

Then:

1. Fork, branch, and keep the change focused.
2. Add a test. Tests here state something that must be true of the model -
   that a fit recovers known coefficients, that a rescaled year meets its level
   exactly - rather than pinning a number that happens to come out.
3. Run `python -m pytest`.
4. Describe *why* in the pull request.

## Releasing

The version comes from the git tag; there is no version number to edit.

1. Move the `[Unreleased]` entries of `CHANGELOG.md` under the new version.
2. Publish a GitHub release whose tag is the version, prefixed with `v`
   (`v0.1.2`).

The publish workflow builds that version and uploads it to PyPI, and Zenodo
archives the release with its own DOI. Between releases, a development install
reports a version like `0.1.3.dev4+gabc1234`.
