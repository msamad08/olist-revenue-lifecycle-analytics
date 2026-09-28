-- Grain: one row per seller with lifecycle status as of the analysis end date
with activity as (
    select i.seller_id,
           min(o.purchased_at)        as first_sale_at,
           max(o.purchased_at)        as last_sale_at,
           count(distinct o.order_id) as orders,
           sum(i.item_price)          as item_revenue
    from {{ ref('stg_order_items') }} i
    join {{ ref('fct_orders') }} o using (order_id)
    where o.is_revenue_order and o.in_analysis_window
    group by 1
)
select s.seller_id,
       s.state,
       a.first_sale_at,
       a.last_sale_at,
       coalesce(a.orders, 0)       as orders,
       coalesce(a.item_revenue, 0) as item_revenue,
       d.mql_id is not null        as acquired_via_marketing_funnel,
       date_diff('day', a.last_sale_at, cast('{{ var("analysis_end_date") }}' as timestamp)) as days_since_last_sale,
       case
           when a.seller_id is null then 'never_sold'
           when date_diff('day', a.last_sale_at, cast('{{ var("analysis_end_date") }}' as timestamp))
                > {{ var('seller_churn_days') }} then 'churned'
           else 'active'
       end as lifecycle_status
from {{ ref('stg_sellers') }} s
left join activity a using (seller_id)
left join {{ ref('stg_closed_deals') }} d using (seller_id)
