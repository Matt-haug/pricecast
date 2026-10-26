"""Draw the documentation's figures.

    python examples/build_doc_figures.py

Needs matplotlib, scipy and the optional dependency (`pip install
"pricecast[entsoe]"`), and an ENTSO-E token in the ENTSOE_TOKEN environment
variable for the first run: the market years it downloads, Belgium 2023 to
2025, are kept in examples/.cache/, so later runs need neither the token nor
the network. Writes ten PNGs to docs/assets/figures/, in the house style of
`figure_style.py`, which the sister package loadcast shares. Each figure's
message is the first sentence of its caption on the page.

    home_week.png               the median week of 2025: the drivers, and the
                                market's price against the model's
    home_extremes.png           the best and the worst week of 2025
    usage_generate.png          the same week: the conditional mean, and the
                                mean with the residual process
    usage_structure.png         the average day and every hour of 2025, market
                                against model
    recipe_2030.png             the average day of 2025 and of 2030, summer
                                and winter
    recipe_floor_level.png      the 2030 year before and after the floor and
                                the level
    recipe_reach.png            the net load of the training years and of 2030
    recipe_calendar.png         a past year laid on the right calendar, and an
                                hour late
    uncertainty_solar.png       the solar fleet from today's to three times it
    uncertainty_samples.png     32 sampled 2035 years

The numbers are those of the pages and of examples/01 to 03; the script prints
the ones the captions quote. The text is set in Manrope when matplotlib can
find it; see figure_style.py.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import qmc  # noqa: E402

import figure_style as fs  # noqa: E402
import pricecast  # noqa: E402

fs.apply()
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "docs" / "assets" / "figures"
CACHE = HERE / ".cache"
S = fs.SERIES

COUNTRY, TZ = "BE", "Europe/Brussels"
HOURS_OF_DAY = [0, 6, 12, 18, 24]


def market_year(year: int) -> tuple[pd.Series, pd.DataFrame]:
    """A market year's prices and drivers, downloaded once and kept."""
    path = CACHE / f"{COUNTRY}_{year}.pkl"
    if path.exists():
        return pd.read_pickle(path)
    from pricecast.entsoe import fetch_year
    data = fetch_year(COUNTRY, year)
    CACHE.mkdir(exist_ok=True)
    pd.to_pickle(data, path)
    return data


def local(data):
    """`data` on the market's wall clock, for plotting."""
    return data.tz_convert(TZ).tz_localize(None)


def week(data, monday: pd.Timestamp):
    """The week of `data` from `monday` to the next, on the wall clock."""
    return local(data).loc[monday:monday + pd.Timedelta(days=7) - pd.Timedelta(hours=1)]


def weekly_correlation(market: pd.Series, model: pd.Series) -> pd.Series:
    """The hourly correlation of model and market over each full week, best first.

    Weeks run from a Monday to the next, on the wall clock; a week cut by the
    start or the end of the year is left out.
    """
    clock = local(market)
    first, last = clock.index[0], clock.index[-1] + pd.Timedelta(hours=1)
    scores = {}
    for monday in pd.date_range(first.normalize(), last, freq="W-MON"):
        if monday < first or monday + pd.Timedelta(days=7) > last:
            continue
        scores[monday] = float(np.corrcoef(week(market, monday), week(model, monday))[0, 1])
    return pd.Series(scores).sort_values(ascending=False)


def average_day(prices: pd.Series, months=None) -> pd.Series:
    """Mean price per local hour, closed at 24 h so the line spans the day."""
    clock = prices.tz_convert(TZ)
    if months is not None:
        clock = clock[clock.index.month.isin(months)]
    day = clock.groupby(clock.index.hour).mean()
    return pd.concat([day, pd.Series([day.iloc[0]], index=[24])])


def by_hour_of_day(ax) -> None:
    ax.set_xticks(HOURS_OF_DAY)
    ax.set_xlabel("hour of the day, local time")


def save(fig, name: str) -> None:
    print("wrote", fs.save(fig, OUT, name))


def on_floor(year: pd.Series, floor: float) -> float:
    return 100.0 * float((year <= floor + 1e-9).mean())


# --------------------------------------------------------------------- usage
def home_and_usage() -> None:
    (p23, d23), (p24, d24), (p25, d25) = (market_year(y) for y in (2023, 2024, 2025))
    model = pricecast.fit([p23, p24], [d23, d24],
                          metadata={"country": COUNTRY, "train_years": [2023, 2024]})
    mean = model.predict(d25, index=p25.index)
    noisy = model.predict(d25, index=p25.index, noise=True, seed=1)
    print("\n2025, the model fitted on 2023-24")
    print(pricecast.compare({"market": p25, "model": mean, "with noise": noisy},
                            truth="market", solar=d25["solar"]).round(2).T)
    # The week shown is the median of 2025's weeks, ranked by how closely the
    # model's hourly prices follow the market's; the best and worst come next.
    ranked = weekly_correlation(p25, mean)
    median_week = ranked.index[len(ranked) // 2]
    print(f"{len(ranked)} full weeks; correlation best {ranked.iloc[0]:.2f} "
          f"({ranked.index[0]:%d %b}), median {ranked.iloc[len(ranked) // 2]:.2f} "
          f"({median_week:%d %b}), worst {ranked.iloc[-1]:.2f} ({ranked.index[-1]:%d %b})")
    market_week, model_week, noisy_week = (week(s, median_week) for s in (p25, mean, noisy))
    hours = market_week.index

    # --- The home page: drivers in, prices out.
    fig, (top, bottom) = plt.subplots(2, 1, figsize=fs.size(2, height=5.0), sharex=True)
    drivers = week(d25, median_week) / 1e3
    for ax in (top, bottom):
        fs.weekends(ax, hours)
    for key in ("load", "wind", "solar"):
        top.plot(hours, drivers[key], color=S[key], lw=1.6)
    fs.heading(top, "GW", subtitle="the drivers: load, solar and wind generation")
    fs.reference(bottom, 0.0)
    bottom.plot(hours, market_week, color=fs.INK, lw=1.6)
    bottom.plot(hours, model_week, color=S["model"], lw=1.6)
    fs.heading(bottom, "EUR/MWh", subtitle="the day-ahead price")
    fs.days(bottom, hours)
    for ax in (top, bottom):
        fs.frame(ax)
    fs.label_ends(top, {key: (hours[-1], drivers[key].iloc[-1], S[key])
                        for key in ("load", "wind", "solar")})
    fs.label_ends(bottom, {"market": (hours[-1], market_week.iloc[-1], fs.INK),
                           "model": (hours[-1], model_week.iloc[-1], S["model"])})
    save(fig, "home_week")

    # --- The best and the worst week of the year, each with its drivers, so
    # that a miss can be read against what the model was given.
    fig, axes = plt.subplots(4, 1, figsize=fs.size(4, height=9.8))
    for (top, bottom), which, position in zip((axes[:2], axes[2:]),
                                              ("the best week", "the worst week"), (0, -1)):
        monday, score = ranked.index[position], ranked.iloc[position]
        bottom.sharex(top)
        market_days, model_days = week(p25, monday), week(mean, monday)
        drivers_days = week(d25, monday) / 1e3
        days_shown = market_days.index
        for ax in (top, bottom):
            fs.weekends(ax, days_shown)
        for key in ("load", "wind", "solar"):
            top.plot(days_shown, drivers_days[key], color=S[key], lw=1.6)
        fs.heading(top, "GW", subtitle=f"{which}, from Monday {monday:%d %B}: "
                                       f"hourly correlation {score:.2f}")
        top.tick_params(labelbottom=False)
        fs.reference(bottom, 0.0)
        bottom.plot(days_shown, market_days, color=fs.INK, lw=1.6)
        bottom.plot(days_shown, model_days, color=S["model"], lw=1.6)
        fs.heading(bottom, "EUR/MWh")
        fs.days(bottom, days_shown)
        for ax in (top, bottom):
            fs.frame(ax)
        fs.label_ends(top, {key: (days_shown[-1], drivers_days[key].iloc[-1], S[key])
                            for key in ("load", "wind", "solar")})
        fs.label_ends(bottom, {"market": (days_shown[-1], market_days.iloc[-1], fs.INK),
                               "model": (days_shown[-1], model_days.iloc[-1], S["model"])})
        print(f"{which}: daily means (drivers GW, prices EUR/MWh)")
        daily = pd.concat([drivers_days, market_days.rename("market"),
                           model_days.rename("model")], axis=1).resample("D").mean()
        print(daily.round(1))
    save(fig, "home_extremes")

    # --- Generate: the conditional mean, and the mean with noise.
    fig, axes = plt.subplots(2, 1, figsize=fs.size(2, height=5.0), sharex=True,
                             sharey=True)
    for ax, (series, subtitle) in zip(axes, (
            (model_week, "model.predict(drivers): the conditional mean"),
            (noisy_week, "model.predict(drivers, noise=True, seed=1)"))):
        fs.weekends(ax, hours)
        fs.reference(ax, 0.0)
        ax.plot(hours, market_week, color=fs.INK, lw=1.4)
        ax.plot(hours, series, color=S["model"], lw=1.6)
        fs.heading(ax, "EUR/MWh", subtitle=subtitle)
    fs.days(axes[-1], hours)
    for ax in axes:
        fs.frame(ax)
    for ax, series in zip(axes, (model_week, noisy_week)):
        fs.label_ends(ax, {"market": (hours[-1], market_week.iloc[-1], fs.INK),
                           "model": (hours[-1], series.iloc[-1], S["model"])})
    save(fig, "usage_generate")

    # --- Check the structure: the average day and the whole year.
    fig, (left, right) = plt.subplots(1, 2, figsize=fs.size(1, height=3.4))
    curves_day, curves_year = {}, {}
    for name, series, colour in (("market", p25, fs.INK), ("model", mean, S["model"])):
        day = average_day(series)
        left.plot(day.index, day.to_numpy(), color=colour)
        curves_day[name] = (day.index, day.to_numpy(), colour)
        ordered = np.sort(series.to_numpy())[::-1]
        share = 100.0 * np.arange(1, ordered.size + 1) / ordered.size
        right.plot(share, ordered, color=colour, lw=1.8)
        curves_year[name] = (share, ordered, colour)
    by_hour_of_day(left)
    fs.heading(left, "EUR/MWh", subtitle="the average day of 2025")
    fs.reference(right, 0.0)
    right.set_xlabel("share of 2025's hours, dearest first (%)")
    fs.heading(right, "EUR/MWh", subtitle="every hour of 2025")
    for ax in (left, right):
        fs.frame(ax)
    fs.label_best(left, curves_day)
    # Where the two years differ: the market's spikes, beside its dearest hours.
    share, ordered, _ = curves_year["market"]
    fs.say(right, share[0], 0.75 * ordered[0], "market", fs.INK, dx=10)
    fs.label_best(right, {"model": curves_year["model"]})
    save(fig, "usage_structure")


# -------------------------------------------------------------------- recipe
def recipe() -> None:
    (p24, d24), (p25, d25) = market_year(2024), market_year(2025)
    model = pricecast.fit([p24, p25], [d24, d25])
    # examples/02_future_year.py: TYNDP 2026 NT+ for 2030, ENTSO-E for 2025.
    solar_2030, wind_2030, demand_2030_twh = 15.64, 7.84, 110.7
    solar_2025 = pricecast.mid_year_capacity(10.70, later=solar_2030, years_between=5)
    wind_2025 = pricecast.mid_year_capacity(5.44, later=wind_2030, years_between=5)
    future = pricecast.scale_drivers(d25, solar=solar_2030 / solar_2025,
                                     wind=wind_2030 / wind_2025,
                                     load=demand_2030_twh / (d25["load"].sum() / 1e6))
    shape = model.predict(future)
    level = 65.1
    training_prices, training = pd.concat([p24, p25]), pd.concat([d24, d25])
    floor = pricecast.training_floor(training_prices)
    year_2030 = pricecast.rescale_to_level(shape, level, floor=floor,
                                           weights=future["load"])
    model_2025 = model.predict(d25)
    beyond = pricecast.share_beyond_training(future, training)
    print(f"\n2030: floor {floor:.1f}, shape mean {shape.mean():.1f} "
          f"(load-weighted {np.average(shape, weights=future['load']):.1f}), "
          f"scale {year_2030.max() / shape.max():.2f}, beyond {beyond:.1f}%, "
          f"on the floor {on_floor(year_2030, floor):.1f}%")
    print(pd.DataFrame({
        "market 2025": pricecast.structure_metrics(p25, solar=d25["solar"]),
        "model 2025": pricecast.structure_metrics(model_2025, solar=d25["solar"]),
        "2030": pricecast.structure_metrics(year_2030, solar=future["solar"]),
    }).round(2))

    # --- Steps 3 to 5: the same weather, 2030's fleet, demand and level.
    fig, axes = plt.subplots(1, 2, figsize=fs.size(1, height=3.4), sharey=True)
    seasons = (("April to September", range(4, 10)),
               ("October to March", (10, 11, 12, 1, 2, 3)))
    lines = (("2025, market", p25, fs.INK), ("2025, model", model_2025, fs.ramp("model", 3)[0]),
             ("2030, model", year_2030, S["model"]))
    season_means = {}
    for ax, (season, months) in zip(axes, seasons):
        fs.reference(ax, 1.0)
        for name, series, colour in lines:
            day = average_day(series, months) / series.mean()
            # The six months' own mean, thin, against the year's at 1.
            in_season = series.tz_convert(TZ)
            in_season = in_season[in_season.index.month.isin(months)]
            season_means[season, name] = in_season.mean() / series.mean()
            ax.axhline(season_means[season, name], color=colour, lw=0.9, zorder=1)
            print(f"{season}, {name}: mean / the year's {season_means[season, name]:.2f}")
            ax.plot(day.index, day.to_numpy(), color=colour)
        by_hour_of_day(ax)
        fs.heading(ax, "price / the year's mean" if ax is axes[0] else "",
                   subtitle=season)
    axes[1].tick_params(labelleft=False)
    for ax in axes:
        fs.frame(ax)
    # Each named once, where no curve comes near: the year's mean over the
    # summer trough, the six months' over winter's quiet night hours.
    fs.say(axes[0], 13, 1.0, "the year's mean", fs.GREY, ha="center", va="bottom",
           dx=0, dy=fs.LABEL_PAD)
    winter_top = max(v for (season, _), v in season_means.items() if season == seasons[1][0])
    fs.say(axes[1], 0.3, winter_top, "the six\nmonths'\nmean", S["model"], ha="left",
           va="bottom", dx=0, dy=fs.LABEL_PAD, linespacing=1.15)
    ends = {}
    for name, series, colour in lines:
        day = average_day(series, seasons[1][1]) / series.mean()
        ends[name] = (24, day.iloc[-1], colour)
    fs.label_ends(axes[1], ends)
    save(fig, "recipe_2030")

    # --- Step 5: the floor and the level.
    fig, ax = plt.subplots(figsize=fs.size(1, height=3.2))
    share = 100.0 * np.arange(1, shape.size + 1) / shape.size
    curves = {"model.predict(future)": (share, np.sort(shape.to_numpy())[::-1],
                                        fs.ramp("model", 3)[0]),
              f"at TYNDP's level, {level:.1f} EUR/MWh, floored":
                  (share, np.sort(year_2030.to_numpy())[::-1], S["model"])}
    for _, (x, y, colour) in curves.items():
        ax.plot(x, y, color=colour)
    fs.reference(ax, floor, label=f"the floor, 2024-25's 1 % quantile: {floor:.0f} EUR/MWh",
                 side="left")
    ax.set_xlabel("share of 2030's hours, dearest first (%)")
    fs.heading(ax, "EUR/MWh")
    fs.frame(ax)
    fs.label_best(ax, curves)
    save(fig, "recipe_floor_level")

    # --- Step 6: how far the model reaches.
    fig, ax = plt.subplots(figsize=fs.size(1, height=3.2))
    curves = {}
    for name, drivers, colour in (("2024-25, the training years", training, fs.INK),
                                  ("2030", future, S["model"])):
        values = np.sort(pricecast.net_load(drivers).to_numpy())[::-1] / 1e3
        share = 100.0 * np.arange(1, values.size + 1) / values.size
        ax.plot(share, values, color=colour)
        curves[name] = (share, values, colour)
    lowest = float(pricecast.net_load(training).min()) / 1e3
    fs.reference(ax, lowest, label="the lowest net load the model was fitted on",
                 side="left")
    ax.set_xlabel("share of the year's hours, highest net load first (%)")
    fs.heading(ax, "GW", subtitle="net load: load minus solar minus wind")
    fs.frame(ax)
    fs.label_best(ax, curves)
    save(fig, "recipe_reach")

    # --- Reusing a past year: laid on the target's market year, or an hour late.
    right = pd.date_range("2025-12-31 23:00", periods=8760, freq="h", tz="UTC")
    late = pd.date_range("2026-01-01 00:00", periods=8760, freq="h", tz="UTC")
    fig, ax = plt.subplots(figsize=fs.size(1, height=3.2))
    curves = {}
    for name, index, colour in (("laid on 2026's market year", right, fs.INK),
                                ("laid an hour late", late, fs.GREY)):
        day = average_day(pricecast.lay_on_calendar(p25, index))
        ax.plot(day.index, day.to_numpy(), color=colour)
        curves[name] = (day.index, day.to_numpy(), colour)
    by_hour_of_day(ax)
    fs.heading(ax, "EUR/MWh", subtitle="2025's prices reused for 2026: the average day")
    fs.frame(ax)
    fs.label_best(ax, curves)
    save(fig, "recipe_calendar")


# --------------------------------------------------------------- uncertainty
def uncertainty() -> None:
    (p24, d24), (p25, d25) = market_year(2024), market_year(2025)
    model = pricecast.load(COUNTRY)
    training = pd.concat([d24, d25])
    floor = pricecast.training_floor(pd.concat([p24, p25]))

    # --- One driver at a time: solar, at 2025's level.
    factors = (1.0, 1.5, 2.0, 2.5, 3.0)
    shades = fs.ramp("solar", len(factors))
    rows, days = {}, {}
    for factor in factors:
        future = pricecast.scale_drivers(d25, solar=factor)
        year = pricecast.rescale_to_level(model.predict(future), level=p25.mean(),
                                          floor=floor)
        days[factor] = average_day(year)
        rows[factor] = {**pricecast.structure_metrics(year, solar=future["solar"]),
                        "beyond training (%)": pricecast.share_beyond_training(future, training),
                        "on the floor (%)": on_floor(year, floor)}
    table = pd.DataFrame(rows).T
    print("\nSolar from x1 to x3, at 2025's level")
    print(table.round(2))

    fig = plt.figure(figsize=fs.size(2, height=4.6))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.35, 1.0])
    left = fig.add_subplot(grid[:, 0])
    for factor, colour in zip(factors, shades):
        left.plot(days[factor].index, days[factor].to_numpy(), color=colour)
    by_hour_of_day(left)
    fs.heading(left, "EUR/MWh", subtitle="the average day, solar fleet x1 to x3")
    upper = fig.add_subplot(grid[0, 1])
    upper.plot(factors, table["Midday / mean (-)"], color=fs.INK, marker="o")
    fs.heading(upper, "midday price / mean")
    upper.tick_params(labelbottom=False)
    lower = fig.add_subplot(grid[1, 1], sharex=upper)
    reach = {"beyond the training net load": (table["beyond training (%)"], fs.INK),
             "on the floor": (table["on the floor (%)"], fs.GREY)}
    for _, (values, colour) in reach.items():
        lower.plot(factors, values, color=colour, marker="o")
    lower.set_xticks(factors)
    lower.set_xlabel("solar fleet, times 2025's")
    fs.heading(lower, "share of hours (%)")
    for ax in (left, upper, lower):
        fs.frame(ax)
    fs.label_ends(left, {f"x{factor:g}": (24, days[factor].iloc[-1], colour)
                         for factor, colour in zip(factors, shades)})
    fs.label_best(lower, {name: (np.array(factors), values.to_numpy(), colour)
                          for name, (values, colour) in reach.items()})
    save(fig, "uncertainty_solar")

    # --- 32 sampled scenarios for 2035, as in examples/03_uncertainty.py.
    low, high = [15.6, 7.8, 122.7, 38.0], [29.5, 17.6, 145.3, 109.3]
    samples = qmc.scale(qmc.Sobol(d=4, seed=1).random(32), low, high)
    solar_2025 = pricecast.mid_year_capacity(10.70, later=15.64, years_between=5)
    wind_2025 = pricecast.mid_year_capacity(5.44, later=7.84, years_between=5)
    demand_2025_twh = d25["load"].sum() / 1e6
    outputs, sampled_days = [], []
    for solar, wind, demand, level in samples:
        future = pricecast.scale_drivers(d25, solar=solar / solar_2025, wind=wind / wind_2025,
                                         load=demand / demand_2025_twh)
        year = pricecast.rescale_to_level(model.predict(future), level, floor=floor,
                                          weights=future["load"])
        sampled_days.append(average_day(year))
        outputs.append({**pricecast.structure_metrics(year, solar=future["solar"]),
                        "beyond training (%)": pricecast.share_beyond_training(future, training),
                        "on the floor (%)": on_floor(year, floor)})
    outputs = pd.DataFrame(outputs)
    print("\n32 sampled years for 2035: P05 / median / P95")
    print(outputs.quantile([0.05, 0.5, 0.95]).T.round(2))

    fig = plt.figure(figsize=fs.size(1, height=3.4))
    grid = fig.add_gridspec(1, 6)
    day_ax = fig.add_subplot(grid[0, :3])
    lines = np.array([day.to_numpy() for day in sampled_days])
    hours = sampled_days[0].index
    for line in lines:
        day_ax.plot(hours, line, color=S["model"], lw=0.7, alpha=0.35)
    median = np.median(lines, axis=0)
    day_ax.plot(hours, median, color=S["model"], lw=2.2)
    by_hour_of_day(day_ax)
    fs.heading(day_ax, "EUR/MWh", subtitle="the average day of each sampled year")
    fs.frame(day_ax)
    fs.say(day_ax, hours[-1], median[-1], "median", S["model"])
    strips = []
    rng = np.random.default_rng(0)
    for position, (key, label) in enumerate((
            ("Midday / mean (-)", "midday / mean"),
            ("Daily 4h spread (EUR/MWh)", "daily spread\n(EUR/MWh)"),
            ("beyond training (%)", "beyond training\n(% of hours)"))):
        ax = fig.add_subplot(grid[0, 3 + position])
        values = outputs[key].to_numpy()
        ax.scatter(rng.uniform(-0.18, 0.18, len(values)), values, s=20,
                   color=S["model"], linewidth=0.6, zorder=3)
        for q in (0.95, 0.5, 0.05):
            ax.hlines(np.quantile(values, q), -0.3, 0.3, color=fs.INK,
                      lw=1.6 if q == 0.5 else 1.0, zorder=4)
        ax.set_xlim(-0.5, 0.5)
        ax.set_xticks([])
        ax.spines["bottom"].set_visible(False)
        fs.heading(ax, label)
        fs.frame(ax, x=False)
        strips.append((ax, values))
    ax, values = strips[-1]
    for name, q in (("P95", 0.95), ("median", 0.5), ("P5", 0.05)):
        fs.say(ax, 0.3, np.quantile(values, q), name, fs.INK)
    save(fig, "uncertainty_samples")


if __name__ == "__main__":
    home_and_usage()
    recipe()
    uncertainty()
