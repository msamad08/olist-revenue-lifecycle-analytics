-- Same person, same day, same basket value: likely split/duplicate checkouts.
-- These inflate order counts (and repeat-customer rates) if not handled.
select customer_unique_id, order_date, gross_revenue, count(*) as order_count,
       string_agg(order_id, ',') as order_ids
from {{ ref('fct_orders') }}
where is_revenue_order
group by 1, 2, 3
having count(*) > 1
