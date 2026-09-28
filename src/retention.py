"""Customer and seller lifecycle: cohort retention, churn, and RFM segmentation."""
import numpy as np
import pandas as pd

from common import REPORTS, plt, query, save

END = pd.Timestamp("2018-08-19")


def customer_cohorts() -> None:
    orders = query("""
        select o.customer_unique_id, date_trunc('month', o.purchased_at) as m, c.cohort_month
        from marts.fct_orders o join marts.dim_customers c using (customer_unique_id)
        where o.is_revenue_order and o.in_analysis_window
    """)
    orders["age"] = ((orders["m"].dt.year - orders["cohort_month"].dt.year) * 12
                     + orders["m"].dt.month - orders["cohort_month"].dt.month)
    size = orders.groupby("cohort_month")["customer_unique_id"].nunique()
    act = orders.groupby(["cohort_month", "age"])["customer_unique_id"].nunique().unstack()
    ret = act.div(size, axis=0) * 100
    ret = ret.loc[(size >= 500).values]  # skip tiny 2016 launch cohorts
    ret.round(2).to_csv(REPORTS / "customer_cohort_retention_pct.csv")

    # Cumulative "ever repurchased within N months"
    cust = query("select * from marts.dim_customers")
    second = query("""
        with r as (select customer_unique_id, purchased_at,
                   row_number() over (partition by customer_unique_id order by purchased_at) rn
                   from marts.fct_orders where is_revenue_order and in_analysis_window)
        select a.customer_unique_id, date_diff('day', a.purchased_at, b.purchased_at) as days_to_second
        from r a join r b on a.customer_unique_id = b.customer_unique_id and a.rn = 1 and b.rn = 2
    """)
    eligible = cust[cust["first_order_at"] <= END - pd.Timedelta(days=180)]
    rep180 = second[second["customer_unique_id"].isin(eligible["customer_unique_id"])
                    & (second["days_to_second"] <= 180)]
    summary = {
        "customers": len(cust),
        "repeat_customer_pct": float(round(100 * cust["is_repeat_customer"].mean(), 2)),
        "repurchase_within_180d_pct": round(100 * len(rep180) / len(eligible), 2),
        "median_days_to_second_order": float(second["days_to_second"].median()),
        "same_day_second_orders_pct": float(round(100 * (second["days_to_second"] == 0).mean(), 1)),
        "revenue_share_from_repeat_customers_pct": float(round(
            100 * cust.loc[cust.is_repeat_customer, "lifetime_revenue"].sum() / cust["lifetime_revenue"].sum(), 1)),
    }
    pd.Series(summary).to_csv(REPORTS / "customer_retention_summary.csv", header=["value"])
    print("  Customer retention:", summary)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    show = ret.iloc[:, 1:13]
    im = ax.imshow(show.values, aspect="auto", cmap="Blues", vmin=0, vmax=np.nanpercentile(show.values, 98))
    ax.set_xticks(range(show.shape[1]), show.columns)
    ax.set_yticks(range(show.shape[0]), [d.strftime("%Y-%m") for d in show.index])
    ax.set_xlabel("Months since first purchase")
    ax.set_title("Customer cohort retention (% of cohort purchasing again)")
    for i in range(show.shape[0]):
        for j in range(show.shape[1]):
            v = show.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7)
    ax.grid(False)
    fig.colorbar(im, ax=ax, label="%")
    save(fig, "customer_cohort_retention.png")


def rfm() -> None:
    c = query("select customer_unique_id, recency_days, order_count, lifetime_revenue from marts.dim_customers")
    c["R"] = pd.qcut(c["recency_days"], 4, labels=[4, 3, 2, 1]).astype(int)
    c["M"] = pd.qcut(c["lifetime_revenue"], 4, labels=[1, 2, 3, 4]).astype(int)
    c["F"] = np.where(c["order_count"] >= 2, 2, 1)  # frequency is ~binary in this marketplace

    def seg(r):
        if r.F == 2 and r.R >= 3: return "Loyal (repeat, recent)"
        if r.F == 2: return "Lapsed repeat buyers"
        if r.R >= 3 and r.M >= 3: return "New high-value"
        if r.R >= 3: return "New low-value"
        if r.M >= 3: return "At-risk high-value one-timers"
        return "Dormant low-value one-timers"
    c["segment"] = c.apply(seg, axis=1)
    out = (c.groupby("segment").agg(customers=("customer_unique_id", "count"),
                                     revenue=("lifetime_revenue", "sum"),
                                     avg_recency_days=("recency_days", "mean"))
           .sort_values("revenue", ascending=False))
    out["customer_pct"] = (100 * out["customers"] / out["customers"].sum()).round(1)
    out["revenue_pct"] = (100 * out["revenue"] / out["revenue"].sum()).round(1)
    out = out.round(0)
    out.to_csv(REPORTS / "rfm_segments.csv")
    c[["customer_unique_id", "R", "F", "M", "segment"]].to_csv(REPORTS / "rfm_customer_scores.csv", index=False)
    print(out.to_string())


def seller_lifecycle() -> None:
    sm = query("select * from marts.fct_seller_monthly")
    # monthly churn: active last month -> inactive this month (excluding the partial last month)
    sm = sm.sort_values(["seller_id", "month"])
    sm["prev_active"] = sm.groupby("seller_id")["is_active"].shift(1)
    last_full = pd.Timestamp("2018-07-01")
    t = sm[sm["prev_active"].notna() & (sm["month"] <= last_full)]
    churn = (t[t["prev_active"] == True].groupby("month")  # noqa: E712
             .agg(active_prev=("seller_id", "count"), churned=("is_active", lambda x: (~x).sum())))
    churn["monthly_churn_pct"] = (100 * churn["churned"] / churn["active_prev"]).round(1)
    churn = churn[churn.index >= "2017-03-01"]
    churn.to_csv(REPORTS / "seller_monthly_churn.csv")

    size = sm[sm["months_since_first_sale"] == 0].groupby("cohort_month")["seller_id"].nunique()
    act = sm[sm["is_active"]].groupby(["cohort_month", "months_since_first_sale"])["seller_id"].nunique().unstack()
    ret = (act.div(size, axis=0) * 100).loc[size[size >= 40].index]
    ret.round(1).to_csv(REPORTS / "seller_cohort_retention_pct.csv")

    status = query("""select lifecycle_status, count(*) sellers, sum(item_revenue) revenue,
                      avg(case when acquired_via_marketing_funnel then 1 else 0 end) as pct_from_funnel
                      from marts.dim_sellers group by 1""")
    status.to_csv(REPORTS / "seller_lifecycle_status.csv", index=False)
    print(status.to_string(index=False))
    print(f"  Avg monthly seller churn (2018): {churn.loc['2018', 'monthly_churn_pct'].mean():.1f}%")

    # Churn vs seller size: are small sellers the ones leaving?
    ds = query("select * from marts.dim_sellers where lifecycle_status <> 'never_sold'")
    ds["size_band"] = pd.cut(ds["orders"], [0, 2, 10, 50, 1e9], labels=["1-2 orders", "3-10", "11-50", "50+"])
    band = ds.groupby("size_band", observed=True).agg(sellers=("seller_id", "count"),
                                                      churned_pct=("lifecycle_status", lambda x: 100 * (x == "churned").mean()))
    band.round(1).to_csv(REPORTS / "seller_churn_by_size.csv")
    print(band.round(1).to_string())

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for cm in ret.index[::3]:
        row = ret.loc[cm].dropna()
        axes[0].plot(row.index, row.values, marker="o", ms=3, label=cm.strftime("%Y-%m"))
    axes[0].set_xlabel("Months since first sale"); axes[0].set_ylabel("% of cohort active")
    axes[0].set_title("Seller cohort retention"); axes[0].legend(fontsize=7, title="Cohort")
    axes[1].plot(churn.index, churn["monthly_churn_pct"], marker="o")
    axes[1].set_title("Monthly seller churn rate"); axes[1].set_ylabel("% of last month's active sellers")
    save(fig, "seller_retention_churn.png")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.bar(band.index.astype(str), band["churned_pct"])
    ax.set_ylabel("% churned (60+ days no sales)"); ax.set_title("Seller churn by lifetime order volume")
    save(fig, "seller_churn_by_size.png")


def main() -> None:
    print("Retention & lifecycle")
    customer_cohorts()
    rfm()
    seller_lifecycle()


if __name__ == "__main__":
    main()
