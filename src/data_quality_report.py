"""Summarize dbt data-quality models into a markdown report with business impact."""
import pandas as pd

from common import REPORTS, plt, query, save

EXPLAIN = {
    "payment_without_items": ("Payments system has a record, order-items system has none",
                              "Mostly canceled/unavailable orders; excluded from revenue"),
    "overpaid_vs_items": ("Payments exceed item price + freight by > R$1",
                          "Consistent with installment interest / vouchers; revenue uses item value, not payments"),
    "underpaid_vs_items": ("Payments short of item price + freight by > R$1", "Flag for finance review"),
    "missing_payment_record": ("Order has items but no payment row", "Flag for finance review"),
    "shipped_before_purchase": ("Carrier pickup timestamp earlier than purchase timestamp",
                                "Timezone/clock skew between logistics and order systems; excluded from delivery-time KPIs"),
    "delivered_before_shipped": ("Customer delivery earlier than carrier pickup", "Exclude from delivery-time KPIs"),
    "delivered_status_no_delivery_date": ("Status 'delivered' but no delivery timestamp", "Status/timestamp drift"),
    "canceled_after_delivery": ("Canceled status but has a delivery timestamp", "Likely returns; not modeled"),
    "product_missing_category": ("Product has no category in the catalog", "Bucketed as 'unknown'"),
    "closed_deal_seller_never_in_seller_table": ("Signed seller (CRM) never appears in marketplace seller table",
                                                 "These sellers never made a sale in the sample: the activation gap"),
    "closed_deal_won_before_first_contact": ("CRM won date earlier than first contact", "Excluded from cycle-time stats"),
    "possible_duplicate_checkout": ("Same customer, same day, same basket value, multiple orders",
                                    "Inflates order counts and repeat-customer rate"),
    "zero_volume_day": ("Day with zero orders after steady volume", "Extract truncation; analysis window ends 2018-08-19"),
    "volume_below_30pct_of_trailing_median": ("Order volume < 30% of trailing 28-day median",
                                              "Extract truncation (plus Christmas Eve 2017, a real seasonal dip)"),
}


def main() -> None:
    print("Data quality report")
    s = query("select * from data_quality.dq_summary")
    impact = query("""
        select issue_type, round(sum(abs(difference)), 2) as brl_affected
        from data_quality.dq_payment_reconciliation group by 1
    """).set_index("issue_type")["brl_affected"]
    rows = []
    for _, r in s.iterrows():
        what, action = EXPLAIN.get(r.issue_type, ("", ""))
        rows.append({"check_group": r.check_group, "issue": r.issue_type, "records": int(r.records),
                     "brl_affected": impact.get(r.issue_type, ""), "what_it_means": what, "handling": action})
    df = pd.DataFrame(rows)
    df.to_csv(REPORTS / "data_quality_findings.csv", index=False)

    tot = query("select count(*) n from marts.fct_orders").n[0]
    md = ["# Data quality findings", "",
          f"Generated from the dbt `data_quality` models. Base: {tot:,} orders across 9 source tables "
          "(orders, items, payments, customers, sellers, products, category translation, CRM leads, CRM deals).", "",
          "| Check | Issue | Records | BRL affected | What it means | Handling |",
          "|---|---|---:|---:|---|---|"]
    for r in rows:
        brl = f"{r['brl_affected']:,.2f}" if r["brl_affected"] != "" else ""
        md.append(f"| {r['check_group']} | `{r['issue']}` | {r['records']:,} | {brl} | {r['what_it_means']} | {r['handling']} |")
    (REPORTS / "data_quality_report.md").write_text("\n".join(md) + "\n")
    print(df[["check_group", "issue", "records"]].to_string(index=False))

    v = query("""select cast(purchased_at as date) d, count(*) n from staging.stg_orders
                 where purchased_at >= '2018-06-01' group by 1 order by 1""")
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(v["d"], v["n"])
    ax.axvline(pd.Timestamp("2018-08-19"), color="k", ls="--", label="analysis window ends")
    ax.axvspan(pd.Timestamp("2018-08-25"), v["d"].max(), color="red", alpha=0.1, label="flagged by dq_volume_anomalies")
    ax.set_title("Daily orders: extract truncation detected automatically")
    ax.set_ylabel("Orders"); ax.legend()
    save(fig, "dq_volume_truncation.png")


if __name__ == "__main__":
    main()
