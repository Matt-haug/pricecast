# AI usage disclosure

> **Author: read this through and edit it before any submission.** The
> statements in "Human review and responsibility" are assertions only you can
> make. They are written here as a checklist of what must be true, not as a
> claim already established. Anything below that does not match what you
> actually did must be corrected - an incomplete or inaccurate disclosure is
> treated by JOSS as an ethical breach.

## Tools used

| Tool | Version / model | Where |
|---|---|---|
| Claude Code (Anthropic) | Claude Opus 5.5 | package code, tests, documentation, parts of the analysis |

Period of use: August-October 2026, during the research behind the accompanying
paper and the extraction of this package from it.

## Nature and scope of assistance

**What preceded the AI assistance.** The modelling approach is the author's own
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
  with AI assistance: the structure metrics, the gas-plant level anchor and its
  backtest, the extrapolation check and the floor, and the worked 2030 example.
  **The author must check each of these against the paper and decide which
  were their own design choices.**
- *Documentation.* Drafting `README.md`, `docs/` and the docstrings.
- *Literature and data survey.* Locating scenario sources (ERAA, TYNDP, PECD,
  World Bank, ECB, EEX). **The author must independently verify every citation
  and every characterisation of another source before submission.**

**Where it was not used.** Not for any correspondence with editors or reviewers.

## Human review and responsibility

*The author confirms, by retaining the statements below, that each is true.*

- The core design decisions were made by the author, not by the tool.
- The author has reviewed, edited and validated the generated code,
  documentation and analysis.
- The author has independently verified the claims made about other software,
  datasets and scenarios, and every citation.
- The author has verified the numerical results reported in the documentation.
- The author is responsible for the accuracy, originality, licensing and
  ethical and legal compliance of everything in this repository.

## Note on the development history

This package was extracted from existing research code over a short period. Any
claim about iterative development should describe the history of the *research
code* separately from the history of this repository, and should not present
this repository's commit history as longer than it is.
