# Metric definitions

One definition per metric, used identically in dbt (SQL), Python, and Power BI (DAX).

| Metric | Definition | Grain / source | Notes |
|---|---|---|---|
| **Gross revenue** | Sum of item price + freight for revenue orders | `fct_orders.gross_revenue` | Uses the order-items system, not payments (payments include installment interest; see data quality report) |
| **Revenue order** | Order with at least one item and status not in (`canceled`, `unavailable`) | `fct_orders.is_revenue_order` | Configurable via dbt var `non_revenue_statuses` |
| **Analysis window** | Orders purchased on or before 2018-08-19 | dbt var `analysis_end_date` | The extract truncates after ~2018-08-22 (`dq_volume_anomalies`) |
| **Customer** | A distinct `customer_unique_id` | `dim_customers` | `customer_id` is per-order in Olist and must not be used to count people |
| **Repeat customer** | Customer with 2+ revenue orders in the window | `dim_customers.is_repeat_customer` | 30% of "second orders" occur the same day as the first (split checkouts), so this overstates true repurchase |
| **Customer cohort retention (month n)** | % of a first-purchase-month cohort placing a revenue order n months later | `reports/customer_cohort_retention_pct.csv` | Cohorts with < 500 customers are excluded |
| **MQL** | Marketing-qualified lead (prospective seller) | `fct_lead_funnel` | 8,000 leads, first contact Jun 2017 to May 2018 |
| **Won** | MQL with a closed deal (seller signed) | `is_won` | |
| **Activated** | Won seller with at least one revenue order | `is_activated` | |
| **Retained seller (funnel)** | Activated seller with sales in 3+ distinct months | `is_retained` | |
| **Mature lead** | First contact at least 120 days before the analysis end | `funnel.py` | Conversion rates use mature leads only, so immature cohorts don't deflate them |
| **Active seller (month)** | Seller with at least one revenue order that month | `fct_seller_monthly.is_active` | |
| **Seller monthly churn** | Sellers active in month m-1 but not in month m, divided by sellers active in m-1 | `reports/seller_monthly_churn.csv` | Month-to-month; sellers can return |
| **Churned seller (status)** | No revenue order in the last 60 days of the window | `dim_sellers.lifecycle_status` | Configurable via dbt var `seller_churn_days` |
| **WAPE** | Sum of absolute weekly forecast errors divided by sum of actuals | `forecast.py` | Backtest: 10 rolling origins, 4-week horizon |
