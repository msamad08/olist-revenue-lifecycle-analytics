"""Weekly revenue forecasting with rolling-origin backtesting.

Models compared:
  - naive:        next week = last week
  - ma4:          4-week moving average
  - holt_damped:  exponential smoothing with damped additive trend
  - reg_trend:    OLS on log revenue with trend + Black Friday/holiday dummies

The winning model (lowest backtest WAPE) produces a 13-week forecast with
80% intervals, rolled up into a monthly revenue plan (low / base / high).
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from common import REPORTS, plt, query, save

HORIZON = 4          # weeks ahead evaluated in each backtest fold
N_FOLDS = 10         # rolling origins
FORECAST_WEEKS = 15  # production forecast length (covers Sep-Nov 2018 in full)


def load_weekly() -> pd.Series:
    df = query("""
        select date_trunc('week', order_date) as week, sum(gross_revenue) as revenue, count(*) as days
        from marts.fct_daily_revenue
        where order_date >= '2017-01-02'   -- first Monday after the 2016 launch gaps
        group by 1 order by 1
    """)
    df = df[df["days"] == 7]  # complete weeks only
    s = df.set_index("week")["revenue"].astype(float)
    s.index = pd.DatetimeIndex(s.index, freq="W-MON")
    return s


def holiday_flags(index: pd.DatetimeIndex) -> pd.DataFrame:
    # Black Friday week (week containing the 4th Friday of Nov) and Christmas week
    flags = pd.DataFrame(index=index)
    bf = []
    for d in index:
        nov = pd.date_range(f"{d.year}-11-01", f"{d.year}-11-30", freq="W-FRI")
        bf_day = nov[3]
        bf.append(int(d <= bf_day < d + pd.Timedelta(days=7)))
    flags["black_friday_week"] = bf
    flags["christmas_week"] = [int(d.month == 12 and 19 <= d.day <= 31) for d in index]
    return flags


def fit_predict(name: str, train: pd.Series, h: int):
    """Return (point_forecast, lower80, upper80) arrays of length h."""
    future_idx = pd.date_range(train.index[-1] + pd.Timedelta(weeks=1), periods=h, freq="W-MON")
    if name == "naive":
        p = np.repeat(train.iloc[-1], h)
        resid = train.diff().dropna()
    elif name == "ma4":
        p = np.repeat(train.iloc[-4:].mean(), h)
        resid = (train - train.rolling(4).mean().shift(1)).dropna()
    elif name == "holt_damped":
        m = ExponentialSmoothing(np.log(train), trend="add", damped_trend=True).fit()
        p = np.exp(m.forecast(h).values)
        resid = train - np.exp(m.fittedvalues)
    elif name == "reg_trend":
        X = sm.add_constant(pd.concat([pd.Series(np.arange(len(train)), index=train.index, name="t"),
                                       np.log1p(pd.Series(np.arange(len(train)), index=train.index, name="log_t")),
                                       holiday_flags(train.index)], axis=1), has_constant="add")
        m = sm.OLS(np.log(train), X).fit()
        t = np.arange(len(train), len(train) + h)
        Xf = sm.add_constant(pd.concat([pd.Series(t, index=future_idx, name="t"),
                                        np.log1p(pd.Series(t, index=future_idx, name="log_t")),
                                        holiday_flags(future_idx)], axis=1), has_constant="add")
        p = np.exp(m.predict(Xf).values)
        resid = train - np.exp(m.fittedvalues)
    else:
        raise ValueError(name)
    # Empirical 80% interval that widens with sqrt(horizon)
    sd = float(np.std(resid[-26:]))
    widen = np.sqrt(np.arange(1, h + 1))
    return p, np.maximum(p - 1.2816 * sd * widen, 0), p + 1.2816 * sd * widen, future_idx


def backtest(s: pd.Series, models):
    rows, step_err = [], []
    for k in range(N_FOLDS, 0, -1):
        cut = len(s) - HORIZON - (k - 1) * 2      # origins every 2 weeks
        train, test = s.iloc[:cut], s.iloc[cut:cut + HORIZON]
        for name in models:
            p, lo, hi, _ = fit_predict(name, train, len(test))
            step_err.extend({"model": name, "step": i + 1, "pct_err": (a - f) / f}
                            for i, (a, f) in enumerate(zip(test.values, p)))
            rows.append({"model": name, "origin": train.index[-1], "actual": test.values.sum(),
                         "abs_err": np.abs(test.values - p).sum(),
                         "total_pct_err": (test.values.sum() - p.sum()) / p.sum(),
                         })
    df = pd.DataFrame(rows)
    out = df.groupby("model").agg(abs_err=("abs_err", "sum"), actual=("actual", "sum"))
    out["WAPE_pct"] = 100 * out["abs_err"] / out["actual"]
    q = df.groupby("model")["total_pct_err"].quantile([0.1, 0.9]).unstack()
    out["period_err_p10"], out["period_err_p90"] = q[0.1], q[0.9]
    out = out[["WAPE_pct", "period_err_p10", "period_err_p90"]].sort_values("WAPE_pct").round(3)
    return out, pd.DataFrame(step_err)


def calibrated_interval(p: np.ndarray, step_err: pd.DataFrame, model: str):
    """80% interval from the backtest's empirical weekly % errors (10th/90th pct) for this model.
    Beyond the backtest horizon, the error band is widened by sqrt(h / HORIZON)."""
    e = step_err[step_err["model"] == model]["pct_err"]
    lo_q, hi_q = e.quantile(0.1), e.quantile(0.9)
    h = np.arange(1, len(p) + 1)
    widen = np.sqrt(np.maximum(h / HORIZON, 1))
    return np.maximum(p * (1 + lo_q * widen), 0), p * (1 + hi_q * widen)


def black_friday_multiplier(s: pd.Series) -> float:
    """Revenue multiplier for Black Friday week, estimated by the regression model."""
    X = sm.add_constant(pd.concat([pd.Series(np.arange(len(s)), index=s.index, name="t"),
                                   np.log1p(pd.Series(np.arange(len(s)), index=s.index, name="log_t")),
                                   holiday_flags(s.index)], axis=1))
    return float(np.exp(sm.OLS(np.log(s), X).fit().params["black_friday_week"]))


def main() -> None:
    print("Revenue forecasting")
    s = load_weekly()
    print(f"  {len(s)} complete weeks: {s.index[0].date()} to {s.index[-1].date()}")
    models = ["naive", "ma4", "holt_damped", "reg_trend"]
    bt, step_err = backtest(s, models)
    bt.to_csv(REPORTS / "forecast_backtest.csv")
    print(bt.to_string())
    best = bt.index[0]

    p, _, _, fidx = fit_predict(best, s, FORECAST_WEEKS)
    lo, hi = calibrated_interval(p, step_err, best)
    fc = pd.DataFrame({"week": fidx, "forecast": p, "lower_80": lo, "upper_80": hi})
    fc[["forecast", "lower_80", "upper_80"]] = fc[["forecast", "lower_80", "upper_80"]].round(0)
    fc.to_csv(REPORTS / "revenue_forecast_weekly.csv", index=False)

    # Monthly plan. Weekly forecasts are allocated to days, then summed by month.
    # The low/high range comes from the backtest's 10th/90th percentile error on
    # 4-week totals (summing weekly interval bounds would overstate uncertainty).
    daily = pd.DataFrame([{"date": d, "base": r["forecast"] / 7}
                          for _, r in fc.iterrows() for d in pd.date_range(r["week"], periods=7)])
    bf_mult = black_friday_multiplier(s)
    bf_weeks = fc.loc[holiday_flags(pd.DatetimeIndex(fc["week"]))["black_friday_week"].values == 1, "week"]
    in_bf = daily["date"].apply(lambda d: any(w <= d < w + pd.Timedelta(days=7) for w in bf_weeks))
    daily["base_with_black_friday"] = np.where(in_bf, daily["base"] * bf_mult, daily["base"])
    daily["month"] = daily["date"].dt.to_period("M")
    full = daily.groupby("month")["date"].agg(lambda x: len(x) == x.iloc[0].days_in_month)
    plan = daily[daily["month"].isin(full[full].index)].groupby("month")[["base", "base_with_black_friday"]].sum()
    lo_q, hi_q = bt.loc[best, "period_err_p10"], bt.loc[best, "period_err_p90"]
    plan["low_p10"] = plan["base_with_black_friday"] * (1 + lo_q)
    plan["high_p90"] = plan["base_with_black_friday"] * (1 + hi_q)
    plan = plan.round(0)
    plan.to_csv(REPORTS / "revenue_plan_monthly.csv")
    print(f"  Black Friday week multiplier (regression estimate): {bf_mult:.2f}x")
    print("  Monthly revenue plan (BRL):\n" + plan.to_string())

    fig, ax = plt.subplots()
    ax.plot(s.index, s.values / 1e3, label="Actual weekly revenue")
    ax.plot(fidx, p / 1e3, "--", label=f"Forecast ({best})")
    ax.fill_between(fidx, lo / 1e3, hi / 1e3, alpha=0.2, label="80% interval (backtest-calibrated)")
    ax.set_ylabel("Revenue (BRL thousands)")
    ax.set_title(f"Weekly revenue: actuals and {FORECAST_WEEKS}-week forecast")
    ax.legend(loc="upper left")
    save(fig, "revenue_forecast.png")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh(bt.index[::-1], bt["WAPE_pct"][::-1])
    ax.set_xlabel("Backtest WAPE (%) — lower is better")
    ax.set_title(f"Model comparison ({N_FOLDS} rolling origins, {HORIZON}-week horizon)")
    save(fig, "forecast_backtest.png")


if __name__ == "__main__":
    main()
