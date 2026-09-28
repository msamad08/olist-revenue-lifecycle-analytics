# DAX measures

Paste these into a `_Measures` table after importing `data/exports/*.csv`.
Definitions match `docs/metric_definitions.md` and the dbt models, so the dashboard and the SQL agree.

## Revenue

```dax
Gross Revenue =
CALCULATE ( SUM ( fct_orders[gross_revenue] ), fct_orders[is_revenue_order] = TRUE () )

Revenue Orders =
CALCULATE ( DISTINCTCOUNT ( fct_orders[order_id] ), fct_orders[is_revenue_order] = TRUE () )

Average Order Value =
DIVIDE ( [Gross Revenue], [Revenue Orders] )

Revenue MoM % =
VAR prev = CALCULATE ( [Gross Revenue], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN DIVIDE ( [Gross Revenue] - prev, prev )

Revenue YoY % =
VAR py = CALCULATE ( [Gross Revenue], SAMEPERIODLASTYEAR ( dim_date[date] ) )
RETURN DIVIDE ( [Gross Revenue] - py, py )
```

## Funnel

```dax
MQLs = COUNTROWS ( fct_lead_funnel )

Won Deals = CALCULATE ( COUNTROWS ( fct_lead_funnel ), fct_lead_funnel[is_won] = TRUE () )

Activated Sellers = CALCULATE ( COUNTROWS ( fct_lead_funnel ), fct_lead_funnel[is_activated] = TRUE () )

Lead-to-Win Rate = DIVIDE ( [Won Deals], [MQLs] )

Win-to-Activation Rate = DIVIDE ( [Activated Sellers], [Won Deals] )

Median Days to Close = MEDIAN ( fct_lead_funnel[days_to_close] )
```

## Retention and churn

```dax
Customers = DISTINCTCOUNT ( dim_customers[customer_unique_id] )

Repeat Customer Rate =
DIVIDE (
    CALCULATE ( [Customers], dim_customers[is_repeat_customer] = TRUE () ),
    [Customers]
)

Active Sellers =
CALCULATE ( DISTINCTCOUNT ( fct_seller_monthly[seller_id] ), fct_seller_monthly[is_active] = TRUE () )

Seller Monthly Churn % =
-- sellers active last month who are inactive this month / sellers active last month
VAR thisMonth = MAX ( fct_seller_monthly[month] )
VAR prevActive =
    CALCULATETABLE (
        VALUES ( fct_seller_monthly[seller_id] ),
        fct_seller_monthly[is_active] = TRUE (),
        fct_seller_monthly[month] = EDATE ( thisMonth, -1 ),
        REMOVEFILTERS ( fct_seller_monthly[month] )
    )
VAR stillActive =
    CALCULATETABLE (
        VALUES ( fct_seller_monthly[seller_id] ),
        fct_seller_monthly[is_active] = TRUE (),
        fct_seller_monthly[month] = thisMonth,
        REMOVEFILTERS ( fct_seller_monthly[month] )
    )
RETURN DIVIDE ( COUNTROWS ( EXCEPT ( prevActive, stillActive ) ), COUNTROWS ( prevActive ) )
```
