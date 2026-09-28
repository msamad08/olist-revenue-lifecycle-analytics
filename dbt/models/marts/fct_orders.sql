-- Grain: one row per order. Revenue = item price + freight (what the marketplace sold).
with items as (
    select
        order_id,
        count(*)                 as item_count,
        count(distinct seller_id) as seller_count,
        sum(item_price)          as item_revenue,
        sum(freight_value)       as freight_revenue
    from {{ ref('stg_order_items') }}
    group by 1
),
payments as (
    select
        order_id,
        sum(payment_value)            as payment_total,
        max(payment_installments)     as max_installments,
        -- primary payment type = the method that paid the most
        arg_max(payment_type, payment_value) as primary_payment_type
    from {{ ref('stg_order_payments') }}
    group by 1
)
select
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.state                                          as customer_state,
    o.order_status,
    o.purchased_at,
    cast(o.purchased_at as date)                     as order_date,
    date_trunc('month', o.purchased_at)              as order_month,
    o.delivered_at,
    o.estimated_delivery_at,
    coalesce(i.item_count, 0)                        as item_count,
    coalesce(i.item_revenue, 0)                      as item_revenue,
    coalesce(i.freight_revenue, 0)                   as freight_revenue,
    coalesce(i.item_revenue, 0) + coalesce(i.freight_revenue, 0) as gross_revenue,
    p.payment_total,
    p.max_installments,
    p.primary_payment_type,
    o.order_status not in (
        {%- for s in var('non_revenue_statuses') %}'{{ s }}'{% if not loop.last %}, {% endif %}{% endfor -%}
    ) and i.order_id is not null                     as is_revenue_order,
    o.purchased_at <= cast('{{ var("analysis_end_date") }}' as timestamp) + interval 1 day as in_analysis_window
from {{ ref('stg_orders') }} o
left join {{ ref('stg_customers') }} c using (customer_id)
left join items i using (order_id)
left join payments p using (order_id)
