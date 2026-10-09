# AI usage disclosure

## Tools used

| Tool | Version / model | Where |
|---|---|---|
| Claude Code (Anthropic) | Claude Opus 5.5 | package code, tests, documentation, parts of the analysis |

Period of use: August-October 2026, during the research behind the accompanying
paper and the extraction of this package from it.

## Nature and scope of assistance

**What preceded the AI assistance.** The modelling approach is the author(s)'s own
research: a single regression of day-ahead price on the clock and on load, solar
and wind generation, generating a full year in one shot as an input to design
studies, judged by what a design optimiser decides rather than by hourly error.

**Where AI assistance was used.**

- *Code generation and refactoring.* Restructuring the research code into this
  standalone package: module layout, public API, the ENTSO-E download helper,
  and the verification that the package reproduces the research code's
  coefficients and predictions to rounding error.
- *Test scaffolding.* Writing the test suite.
- *Analysis.* Several parts of the accompanying analysis were proposed and run
  with AI assistance: fitting campaigns on large number of years across countries 
- *Documentation.* Drafting `README.md`, `docs/` and the docstrings.
- *Data fetching.* Scenario sources (ERAA, TYNDP, PECD,
  World Bank, ECB, EEX). ENTSO-E data through public API

**Where it was not used.** Not for any correspondence with editors or reviewers.

## Human review and responsibility

*The author confirms, by retaining the statements below, that each is true.*

- The core design decisions were made by the author(s), not by the tool.
- The author(s) has reviewed, edited and validated the generated code,
  documentation and analysis.
- The author(s) has independently verified the claims made about other software,
  datasets and scenarios, and every citation.
- The author(s) has verified the numerical results reported in the documentation.
- The author(s) is responsible for the accuracy, originality, licensing and
  ethical and legal compliance of everything in this repository.

## Note on the development history

This package was extracted from existing research code over a short period. Any
claim about iterative development should describe the history of the *research
code* separately from the history of this repository, and should not present
this repository's commit history as longer than it is.
