-- Grain: seller x month, from the seller's first sale month to the end of the analysis window.
-- A seller is "active" in a month if they had >=1 revenue order.
with sales as (
    select i.seller_id,
           date_trunc('month', o.purchased_at) as month,
           count(distinct o.order_id)          as orders,
           sum(i.item_price)                   as item_revenue
    from {{ ref('stg_order_items') }} i
    join {{ ref('fct_orders') }} o using (order_id)
    where o.is_revenue_order and o.in_analysis_window
    group by 1, 2
),
first_sale as (
    select seller_id, min(month) as cohort_month from sales group by 1
),
spine as (
    select f.seller_id, f.cohort_month,
           cast(unnest(generate_series(f.cohort_month,
                   date_trunc('month', cast('{{ var("analysis_end_date") }}' as timestamp)),
                   interval 1 month)) as timestamp) as month
    from first_sale f
)
select s.seller_id,
       s.cohort_month,
       s.month,
       date_diff('month', s.cohort_month, s.month) as months_since_first_sale,
       coalesce(x.orders, 0)          as orders,
       coalesce(x.item_revenue, 0)    as item_revenue,
       x.seller_id is not null        as is_active
from spine s
left join sales x on x.seller_id = s.seller_id and x.month = s.month
