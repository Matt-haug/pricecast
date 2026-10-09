# Mathematics

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
$\varepsilon_t$ is the residual. 33 regressors and an intercept.

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

## The level

$$C = \frac{p_{\mathrm{gas}}}{\eta} + \frac{e\,p_{\mathrm{CO_2}}}{\eta}, \qquad
k = \frac{\bar p_{\mathrm{past}}}{C_{\mathrm{past}}}, \qquad
\bar p_{\mathrm{target}} = k\, C_{\mathrm{target}}$$

where $C$ is the running cost of a combined-cycle gas plant (EUR/MWh of
electricity), $p_{\mathrm{gas}}$ the gas price (EUR/MWh of fuel),
$p_{\mathrm{CO_2}}$ the carbon price (EUR/t), $\eta = 0.55$ the plant's net
efficiency, $e = 0.202$ t CO$_2$ per MWh of gas (IPCC default, 56.1 t/TJ),
$\bar p$ a year's mean day-ahead price, and $k$ the market's ratio of the two.

Rescaling to a level $\bar p_{\mathrm{target}}$ multiplies the generated year by
$\bar p_{\mathrm{target}} / \bar p_{\mathrm{model}}$. With a floor $f$, the
scale $a$ is instead the solution of

$$\frac{1}{T}\sum_t \max(a\, p_t,\, f) = \bar p_{\mathrm{target}}$$

where $T$ is the number of hours, found by bisection, so the level is met
exactly after clipping.

## The reach

$$\text{share beyond training} = \frac{100}{T} \sum_t
\mathbf 1\!\left[N_t < \min_{\tau \in \text{training}} N_\tau\right], \qquad
N_t = L_t - S_t - W_t$$

where $N_t$ is the net load and $\mathbf 1[\cdot]$ is 1 when its argument holds.

## Nomenclature

| symbol | meaning | unit |
|---|---|---|
| $p_t$ | day-ahead price in hour $t$ | EUR/MWh |
| $D_{h,t}$, $E_{d,t}$ | hour-of-day and weekday indicators | - |
| $L_t$, $S_t$, $W_t$ | load, solar and wind generation | MW |
| $N_t$ | net load, $L_t - S_t - W_t$ | MW |
| $\beta_\bullet$ | regression coefficients | EUR/MWh per unit |
| $\varepsilon_t$ | residual | EUR/MWh |
| $\sigma$ | residual standard deviation | EUR/MWh |
| $\nu$, $\kappa$ | Student-t degrees of freedom, excess kurtosis | - |
| $C$ | gas plant running cost | EUR/MWh |
| $p_{\mathrm{gas}}$, $p_{\mathrm{CO_2}}$ | gas and carbon prices | EUR/MWh, EUR/t |
| $\eta$, $e$ | plant efficiency, emission factor of gas | -, t/MWh |
| $k$ | mean price over gas plant cost | - |
| $\bar p$ | mean price of a year | EUR/MWh |
| $f$, $a$ | price floor, rescaling factor | EUR/MWh, - |
| $T$ | number of hours | - |
