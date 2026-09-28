# Data quality findings

Generated from the dbt `data_quality` models. Base: 99,441 orders across 9 source tables (orders, items, payments, customers, sellers, products, category translation, CRM leads, CRM deals).

| Check | Issue | Records | BRL affected | What it means | Handling |
|---|---|---:|---:|---|---|
| duplicates | `possible_duplicate_checkout` | 119 |  | Same customer, same day, same basket value, multiple orders | Inflates order counts and repeat-customer rate |
| order_lifecycle | `shipped_before_purchase` | 166 |  | Carrier pickup timestamp earlier than purchase timestamp | Timezone/clock skew between logistics and order systems; excluded from delivery-time KPIs |
| order_lifecycle | `delivered_before_shipped` | 23 |  | Customer delivery earlier than carrier pickup | Exclude from delivery-time KPIs |
| order_lifecycle | `delivered_status_no_delivery_date` | 8 |  | Status 'delivered' but no delivery timestamp | Status/timestamp drift |
| order_lifecycle | `canceled_after_delivery` | 6 |  | Canceled status but has a delivery timestamp | Likely returns; not modeled |
| payment_reconciliation | `payment_without_items` | 775 | 162,591.95 | Payments system has a record, order-items system has none | Mostly canceled/unavailable orders; excluded from revenue |
| payment_reconciliation | `overpaid_vs_items` | 232 | 3,064.76 | Payments exceed item price + freight by > R$1 | Consistent with installment interest / vouchers; revenue uses item value, not payments |
| payment_reconciliation | `underpaid_vs_items` | 17 | 197.57 | Payments short of item price + freight by > R$1 | Flag for finance review |
| payment_reconciliation | `missing_payment_record` | 1 | 143.46 | Order has items but no payment row | Flag for finance review |
| referential_integrity | `product_missing_category` | 610 |  | Product has no category in the catalog | Bucketed as 'unknown' |
| referential_integrity | `closed_deal_seller_never_in_seller_table` | 462 |  | Signed seller (CRM) never appears in marketplace seller table | These sellers never made a sale in the sample: the activation gap |
| referential_integrity | `closed_deal_won_before_first_contact` | 1 |  | CRM won date earlier than first contact | Excluded from cycle-time stats |
| volume | `volume_below_30pct_of_trailing_median` | 13 |  | Order volume < 30% of trailing 28-day median | Extract truncation (plus Christmas Eve 2017, a real seasonal dip) |
| volume | `zero_volume_day` | 7 |  | Day with zero orders after steady volume | Extract truncation; analysis window ends 2018-08-19 |
