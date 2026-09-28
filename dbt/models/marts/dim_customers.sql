-- Grain: one row per real customer (customer_unique_id). Lifecycle + RFM inputs.
with o as (
    select * from {{ ref('fct_orders') }} where is_revenue_order and in_analysis_window
)
select
    customer_unique_id,
    min(purchased_at)                              as first_order_at,
    max(purchased_at)                              as last_order_at,
    date_trunc('month', min(purchased_at))         as cohort_month,
    count(distinct order_id)                       as order_count,
    sum(gross_revenue)                             as lifetime_revenue,
    date_diff('day', max(purchased_at), cast('{{ var("analysis_end_date") }}' as timestamp)) as recency_days,
    count(distinct order_id) > 1                   as is_repeat_customer,
    arg_min(customer_state, purchased_at)          as first_state
from o
group by 1
