"""Export the star schema to CSV for Power BI (Get Data > Text/CSV).

Outputs go to data/exports/ (git-ignored). In Power BI, relate:
  fct_orders[customer_unique_id] -> dim_customers[customer_unique_id]  (many-to-one)
  fct_orders[order_date]         -> dim_date[date]                      (many-to-one)
  fct_lead_funnel[seller_id]     -> dim_sellers[seller_id]              (many-to-one)
  fct_seller_monthly[seller_id]  -> dim_sellers[seller_id]              (many-to-one)
"""
from common import ROOT, query

OUT = ROOT / "data" / "exports"
OUT.mkdir(parents=True, exist_ok=True)

TABLES = {
    "fct_orders": "select * from marts.fct_orders where in_analysis_window",
    "fct_daily_revenue": "select * from marts.fct_daily_revenue",
    "fct_lead_funnel": "select * from marts.fct_lead_funnel",
    "fct_seller_monthly": "select * from marts.fct_seller_monthly",
    "dim_customers": "select * from marts.dim_customers",
    "dim_sellers": "select * from marts.dim_sellers",
    "dim_date": """select cast(d as date) as date, year(d) as year, month(d) as month,
                          strftime(d, '%Y-%m') as year_month, dayofweek(d) as day_of_week,
                          cast(date_trunc('week', d) as date) as week_start
                   from (select unnest(generate_series(date '2016-09-01', date '2018-12-31', interval 1 day)) as d)""",
    "dq_findings": "select * from data_quality.dq_summary",
}


def main() -> None:
    print("Power BI export")
    for name, sql in TABLES.items():
        df = query(sql)
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"  data/exports/{name}.csv  ({len(df):,} rows)")


if __name__ == "__main__":
    main()
