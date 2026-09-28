"""Seller-acquisition funnel: MQL -> won deal -> activated (first sale) -> retained (3+ active months).

Only "mature" leads are used for stage conversion rates, so that recent leads
that haven't had time to close/activate don't drag the rates down.
"""
import numpy as np
import pandas as pd

from common import REPORTS, plt, query, save

ANALYSIS_END = pd.Timestamp("2018-08-19")
MATURITY_DAYS = 120  # lead must be >= this old at analysis end to be scored


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return c - h, c + h


def main() -> None:
    print("Sales funnel")
    f = query("select * from marts.fct_lead_funnel")
    f["first_contact_date"] = pd.to_datetime(f["first_contact_date"])
    mature = f[f["first_contact_date"] <= ANALYSIS_END - pd.Timedelta(days=MATURITY_DAYS)].copy()
    # A deal won after the analysis window can't have activated yet; treat as not-yet-won for mature scoring
    late = pd.to_datetime(mature["won_at"]) > ANALYSIS_END
    mature.loc[late, ["is_won", "is_activated", "is_retained"]] = False
    print(f"  {len(f):,} MQLs total; {len(mature):,} mature (first contact <= "
          f"{(ANALYSIS_END - pd.Timedelta(days=MATURITY_DAYS)).date()})")

    stages = [("MQL", len(mature)), ("Won (signed)", int(mature.is_won.sum())),
              ("Activated (1st sale)", int(mature.is_activated.sum())),
              ("Retained (3+ active mo.)", int(mature.is_retained.sum()))]
    funnel = pd.DataFrame(stages, columns=["stage", "count"])
    funnel["pct_of_mql"] = (100 * funnel["count"] / funnel["count"].iloc[0]).round(2)
    funnel["step_conversion_pct"] = (100 * funnel["count"] / funnel["count"].shift(1)).round(1)
    funnel.to_csv(REPORTS / "funnel_overall.csv", index=False)
    print(funnel.to_string(index=False))

    by = (mature.groupby("origin")
          .agg(mqls=("mql_id", "count"), won=("is_won", "sum"), activated=("is_activated", "sum"))
          .sort_values("mqls", ascending=False))
    by["win_rate_pct"] = 100 * by["won"] / by["mqls"]
    ci = [wilson(k, n) for k, n in zip(by["won"], by["mqls"])]
    by["win_ci_low"] = [100 * c[0] for c in ci]
    by["win_ci_high"] = [100 * c[1] for c in ci]
    by["activation_of_won_pct"] = 100 * by["activated"] / by["won"].replace(0, np.nan)
    by = by.round(1)
    by.to_csv(REPORTS / "funnel_by_origin.csv")
    print(by.to_string())

    won = f[f["is_won"]].copy()
    seg = (won.groupby("business_segment")
           .agg(won=("mql_id", "count"), activated=("is_activated", "sum"),
                median_days_to_close=("days_to_close", "median"),
                seller_revenue=("seller_item_revenue", "sum"))
           .query("won >= 15").sort_values("won", ascending=False))
    seg["activation_pct"] = (100 * seg["activated"] / seg["won"]).round(1)
    seg.to_csv(REPORTS / "funnel_by_segment.csv")

    timing = pd.DataFrame({
        "metric": ["days_to_close", "days_won_to_first_sale"],
        "median": [f["days_to_close"].median(), f["days_won_to_first_sale"].median()],
        "p75": [f["days_to_close"].quantile(.75), f["days_won_to_first_sale"].quantile(.75)],
        "p90": [f["days_to_close"].quantile(.9), f["days_won_to_first_sale"].quantile(.9)],
    })
    timing.to_csv(REPORTS / "funnel_timing.csv", index=False)
    print(timing.to_string(index=False))

    # --- charts
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.barh(funnel["stage"][::-1], funnel["count"][::-1])
    for i, (c, p) in enumerate(zip(funnel["count"][::-1], funnel["pct_of_mql"][::-1])):
        ax.text(c, i, f"  {c:,} ({p}%)", va="center")
    ax.set_xlim(0, funnel["count"].max() * 1.25)
    ax.set_title("Seller acquisition funnel (mature leads)")
    ax.grid(False)
    save(fig, "funnel_overall.png")

    top = by[by["mqls"] >= 50].sort_values("win_rate_pct")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.errorbar(top["win_rate_pct"], top.index, fmt="o",
                xerr=[top["win_rate_pct"] - top["win_ci_low"], top["win_ci_high"] - top["win_rate_pct"]])
    ax.set_xlabel("Lead -> won rate (%), 95% Wilson CI")
    ax.set_title("Win rate by lead origin (origins with 50+ mature MQLs)")
    save(fig, "funnel_win_rate_by_origin.png")

    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.hist(f["days_to_close"].dropna().clip(upper=200), bins=40)
    ax.axvline(f["days_to_close"].median(), color="k", ls="--", label=f"median {f['days_to_close'].median():.0f} days")
    ax.set_xlabel("Days from first contact to won (clipped at 200)")
    ax.set_title("Sales cycle length")
    ax.legend()
    save(fig, "funnel_days_to_close.png")


if __name__ == "__main__":
    main()
