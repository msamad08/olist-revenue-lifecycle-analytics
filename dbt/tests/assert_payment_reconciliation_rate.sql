-- Warn (not fail) if more than 2% of revenue orders fail payment reconciliation.
{{ config(severity='warn') }}
select round(100.0 * count(r.order_id) / count(*), 2) as pct_unreconciled
from {{ ref('fct_orders') }} o
left join {{ ref('dq_payment_reconciliation') }} r using (order_id)
where o.is_revenue_order
having 100.0 * count(r.order_id) / count(*) > 2
