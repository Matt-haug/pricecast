# Mathematics

Nothing on this page is new time-series theory. The model is a regression of
the price on calendar terms and on external drivers, and its noise a moving
average of independent draws; Box et al. (2015) treat both. What `pricecast`
adds is the choice of drivers and terms that makes a generated year respond to
a scenario's demand and fleet as real prices have.

## The model

One ordinary least-squares regression on hourly day-ahead price:

$$p_t = \beta_0 + \sum_{h=1}^{23} \beta_h D_{h,t} + \sum_{d=0}^{5} \beta_d E_{d,t}
+ \beta_L L_t + \beta_S S_t + \beta_W W_t
+ \beta_Q \max\!\left(L_t - S_t - W_t,\, 0\right)^2 + \varepsilon_t$$

where $p_t$ is the day-ahead price in hour $t$ (EUR/MWh); $D_{h,t}$ is 1 in
hour-of-day $h$ and 0 otherwise, hour 0 being the reference; $E_{d,t}$ is 1 on
weekday $d$ (Monday $=0$ to Saturday $=5$) and 0 otherwise, Sunday being the
reference; $L_t$, $S_t$ and $W_t$ are load, solar generation and wind generation
(MW); $\beta_\bullet$ are the fitted coefficients, $\beta_L$, $\beta_S$,
$\beta_W$ in EUR/MWh per MW and $\beta_Q$ in EUR/MWh per MW$^2$; and
$\varepsilon_t$ is the residual. 33 regressors and an intercept. The generated
price $\hat p_t$ is the right-hand side evaluated on the drivers of the year
wanted, with $\varepsilon_t = 0$ (the conditional mean) or with the residual
process below.

The quadratic term is the **net-load curvature**. On 2023-24 data it was
negative in all five markets studied - the price response flattens as residual
demand rises - but it is small, and its sign can change with the window.

Hour and weekday are read on UTC by default, which is how the shipped models
were fitted; the `timezone` feature option reads them on local time instead.
Optional lags of the drivers (`driver_lags`) were tested and are worth almost
nothing.

A year is generated **in one shot**: the drivers of every hour go through the
regression, with no autoregression on the price.

## The residual process

With `noise=True`, a residual process is added:

$$\varepsilon_t = \sigma\, \frac{\tilde z_t}{\operatorname{sd}(\tilde z)}, \qquad
\tilde z_t = \frac{1}{24}\sum_{k} z_{t+k}, \qquad
z_t \sim \sqrt{\tfrac{\nu-2}{\nu}}\; t_\nu$$

where $\sigma$ is the standard deviation of the fitted residuals; $z_t$ are
Student-t draws with $\nu$ degrees of freedom, scaled to unit variance; $\nu$ is
set from the residuals' excess kurtosis $\kappa$ as $\nu = 4 + 6/\kappa$, kept
within 4.2-60; and $\tilde z_t$ is their centred 24-hour moving average, which
gives the noise the day-scale persistence of the real residual. The noisy hours
are uncorrelated with the real ones.

## The level and the floor

The level of a year is set from outside, as the scenario reports it. Rescaling
multiplies the generated year $\hat p_t$ by a factor $a$; with a floor $f$, the
year is clipped at the floor *after* scaling, and $a$ is the solution of

$$\frac{\sum_t w_t \max\left(a\, \hat p_t,\, f\right)}{\sum_t w_t} = \bar p$$

where $\hat p_t$ is the generated price in hour $t$ (EUR/MWh); $a$ the scale
factor (-), found by bisection so that the level is met exactly after clipping;
$f$ the floor (EUR/MWh), by default the 1% quantile of the training prices;
$w_t$ the weight of hour $t$ - the hourly load $L_t$ to match a load-weighted
mean, as TYNDP reports it, or 1 for a plain mean; and $\bar p$ the target level
(EUR/MWh). Without a floor, $a = \bar p\, \sum_t w_t / \sum_t w_t \hat p_t$.

When the model is fitted on a scenario's hourly results, the hours priced at or
above a scarcity threshold $p^{\mathrm{sc}}$ (1000 EUR/MWh for TYNDP 2026) are
left out of the fit, of the floor and of the level, which is then

$$\bar p = \sum_{s} \pi_s\,
\frac{\sum_{t \in \mathcal O_s} L_{s,t}\, p_{s,t}}{\sum_{t \in \mathcal O_s} L_{s,t}}$$

where $s$ runs over the scenario's weather scenarios for the target year;
$\pi_s$ is the probability the scenario gives weather scenario $s$, with
$\sum_s \pi_s = 1$; $p_{s,t}$ and $L_{s,t}$ are its price (EUR/MWh) and load
(MW) in hour $t$; and $\mathcal O_s$ is its set of ordinary hours, those with
$p_{s,t} < p^{\mathrm{sc}}$.

## The reach

Two counts say how far a year lies from the data the model was fitted on:

$$\rho^{\mathrm{net}} = \frac{100}{T} \sum_t
\mathbf 1\!\left[N_t < \min_{\tau \in \mathcal F} N_\tau\right], \qquad
\rho^{\mathrm{fl}} = \frac{100}{T} \sum_t \mathbf 1\!\left[a\,\hat p_t \le f\right]$$

where $\rho^{\mathrm{net}}$ is the share of hours beyond the training net load
(%, `share_beyond_training`); $\rho^{\mathrm{fl}}$ the share of hours left on
the floor after rescaling (%); $T$ the number of hours of the year; $N_t$ the
net load of hour $t$ (MW); $\mathcal F$ the hours the model was fitted on; and
$\mathbf 1[\cdot]$ is 1 when its argument holds and 0 otherwise. While both stay at a few percent, the year can
be used; past that, the scenario's own hourly prices are the better input.

## Nomenclature

| symbol | meaning | unit |
|---|---|---|
| $p_t$ | day-ahead price in hour $t$ | EUR/MWh |
| $\hat p_t$ | price generated by the model, before rescaling | EUR/MWh |
| $D_{h,t}$, $E_{d,t}$ | hour-of-day and weekday indicators | - |
| $L_t$, $S_t$, $W_t$ | load, solar and wind generation | MW |
| $N_t$ | net load, $L_t - S_t - W_t$ | MW |
| $\beta_\bullet$ | regression coefficients | EUR/MWh per unit |
| $\varepsilon_t$ | residual | EUR/MWh |
| $\sigma$ | residual standard deviation | EUR/MWh |
| $\nu$, $\kappa$ | Student-t degrees of freedom, excess kurtosis | - |
| $\bar p$ | target level, a mean price | EUR/MWh |
| $a$, $f$ | rescaling factor, price floor | -, EUR/MWh |
| $w_t$ | weight of hour $t$ in the level | MW or - |
| $p^{\mathrm{sc}}$ | scarcity threshold | EUR/MWh |
| $s$, $\pi_s$, $\mathcal O_s$ | weather scenario, its probability, its ordinary hours | - |
| $\rho^{\mathrm{net}}$, $\rho^{\mathrm{fl}}$ | shares of hours beyond the training net load and on the floor | % |
| $T$, $\mathcal F$ | number of hours of the year, hours the model was fitted on | - |

## Reference

Box GEP, Jenkins GM, Reinsel GC, Ljung GM. *Time Series Analysis: Forecasting
and Control*, 5th edition. Wiley, Hoboken, NJ, 2015. ISBN 978-1-118-67502-1.
