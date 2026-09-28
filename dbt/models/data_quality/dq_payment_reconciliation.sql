-- Cross-source check: the payments system vs. the order-items system.
-- Every non-canceled order should have payments that sum to item price + freight.
select
    order_id,
    order_status,
    purchased_at,
    gross_revenue,
    payment_total,
    round(coalesce(payment_total, 0) - gross_revenue, 2) as difference,
    case
        when payment_total is null and item_count = 0 then 'no_payment_and_no_items'
        when payment_total is null                     then 'missing_payment_record'
        when item_count = 0                            then 'payment_without_items'
        when payment_total - gross_revenue > {{ var('payment_tolerance_brl') }} then 'overpaid_vs_items'
        when gross_revenue - payment_total > {{ var('payment_tolerance_brl') }} then 'underpaid_vs_items'
    end as issue_type
from {{ ref('fct_orders') }}
where
    payment_total is null
    or item_count = 0
    or abs(payment_total - gross_revenue) > {{ var('payment_tolerance_brl') }}
