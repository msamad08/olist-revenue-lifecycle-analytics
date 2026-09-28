# Power BI dashboard spec

Four pages. Every visual uses measures from `dax_measures.md`; every metric is defined in `docs/metric_definitions.md`.

## Page 1: Revenue & forecast
- KPI cards: Gross Revenue, Revenue Orders, Average Order Value, Revenue MoM %
- Line chart: weekly Gross Revenue (dim_date[week_start]) with `reports/revenue_forecast_weekly.csv` forecast and 80% band
- Table: monthly revenue plan (`reports/revenue_plan_monthly.csv`): base, base with Black Friday, low (P10), high (P90)
- Slicers: customer_state, primary_payment_type

## Page 2: Seller acquisition funnel
- Funnel visual: MQLs > Won Deals > Activated Sellers > Retained
- Clustered bar: Lead-to-Win Rate by origin (sorted), with MQL count in tooltip
- Bar: Win-to-Activation Rate by business_segment
- Card: Median Days to Close

## Page 3: Retention & lifecycle
- Matrix heatmap: customer cohort (rows) x months since first purchase (columns), conditional formatting
- Line: Seller Monthly Churn %
- Bar: seller churn % by lifetime order band
- Donut: RFM segment share of revenue (`reports/rfm_segments.csv`)

## Page 4: Data quality
- Table: `dq_findings` (check group, issue, records), conditional icon by severity
- Line: daily orders with the truncation window highlighted
- Text box: what each check means and how it is handled (from `reports/data_quality_report.md`)
