-- Days whose order volume collapses vs. the trailing 28-day median.
-- Catches extraction gaps/truncation that would otherwise look like a business decline.
-- Runs on ALL orders (not just the analysis window) so the truncated tail is visible.
with bounds as (
    select min(cast(purchased_at as date)) d0, max(cast(purchased_at as date)) d1 from {{ ref('stg_orders') }}
),
days as (select cast(unnest(generate_series(d0, d1, interval 1 day)) as date) as d from bounds),
daily as (
    select d, count(o.order_id) as orders
    from days left join {{ ref('stg_orders') }} o on cast(o.purchased_at as date) = d
    group by 1
),
scored as (
    select d, orders,
           median(orders) over (order by d rows between 28 preceding and 1 preceding) as trailing_median
    from daily
)
select d as order_date, orders, trailing_median,
       round(orders / nullif(trailing_median, 0), 3) as ratio_to_trailing_median,
       case when orders = 0 then 'zero_volume_day' else 'volume_below_30pct_of_trailing_median' end as issue_type
from scored
where trailing_median >= 20 and orders < 0.3 * trailing_median
order by 1
