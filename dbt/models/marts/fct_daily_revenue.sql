-- Grain: one row per calendar day (gap-filled) within the analysis window
with bounds as (
    select min(order_date) as d0, cast('{{ var("analysis_end_date") }}' as date) as d1
    from {{ ref('fct_orders') }} where is_revenue_order
),
days as (
    select cast(unnest(generate_series(d0, d1, interval 1 day)) as date) as order_date from bounds
),
agg as (
    select order_date,
           count(*)                          as orders,
           count(distinct customer_unique_id) as customers,
           sum(gross_revenue)                as gross_revenue,
           sum(item_revenue)                 as item_revenue
    from {{ ref('fct_orders') }}
    where is_revenue_order and in_analysis_window
    group by 1
)
select d.order_date,
       coalesce(a.orders, 0)        as orders,
       coalesce(a.customers, 0)     as customers,
       coalesce(a.gross_revenue, 0) as gross_revenue,
       coalesce(a.item_revenue, 0)  as item_revenue
from days d left join agg a using (order_date)
