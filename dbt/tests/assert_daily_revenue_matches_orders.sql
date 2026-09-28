-- The daily series must sum to the same total as the order fact (no rows lost in gap-filling)
select 1
from (select sum(gross_revenue) s from {{ ref('fct_daily_revenue') }}) d,
     (select sum(gross_revenue) s from {{ ref('fct_orders') }} where is_revenue_order and in_analysis_window) o
where abs(d.s - o.s) > 0.01
