-- Grain: one row per marketing-qualified lead (MQL).
-- Funnel: MQL -> closed deal (seller signed) -> activated (first sale) -> retained (sold in 3+ distinct months)
with first_sales as (
    select seller_id,
           min(month) as first_sale_month,
           min(month) filter (where is_active) as first_active_month,
           count(*) filter (where is_active)  as active_months,
           sum(item_revenue)                  as item_revenue
    from {{ ref('fct_seller_monthly') }}
    group by 1
),
first_sale_ts as (
    select i.seller_id, min(o.purchased_at) as first_sale_at
    from {{ ref('stg_order_items') }} i
    join {{ ref('fct_orders') }} o using (order_id)
    where o.is_revenue_order and o.in_analysis_window
    group by 1
)
select
    l.mql_id,
    l.origin,
    l.landing_page_id,
    l.first_contact_date,
    date_trunc('month', l.first_contact_date)                    as lead_month,
    d.seller_id,
    d.won_at,
    d.business_segment,
    d.lead_type,
    d.business_type,
    fs.first_sale_at,
    coalesce(f.active_months, 0)                                 as active_months,
    coalesce(f.item_revenue, 0)                                  as seller_item_revenue,
    d.mql_id is not null                                         as is_won,
    fs.first_sale_at is not null                                 as is_activated,
    coalesce(f.active_months, 0) >= 3                            as is_retained,
    date_diff('day', l.first_contact_date, cast(d.won_at as date))       as days_to_close,
    date_diff('day', cast(d.won_at as date), cast(fs.first_sale_at as date)) as days_won_to_first_sale
from {{ ref('stg_leads') }} l
left join {{ ref('stg_closed_deals') }} d using (mql_id)
left join first_sales f on f.seller_id = d.seller_id
left join first_sale_ts fs on fs.seller_id = d.seller_id
