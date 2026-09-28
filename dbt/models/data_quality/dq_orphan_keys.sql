-- Referential integrity across source tables
select 'order_item_seller_not_in_sellers' as issue_type, i.order_id as record_id
from {{ ref('stg_order_items') }} i left join {{ ref('stg_sellers') }} s using (seller_id)
where s.seller_id is null
union all
select 'order_item_product_not_in_products', i.order_id
from {{ ref('stg_order_items') }} i left join {{ ref('stg_products') }} p using (product_id)
where p.product_id is null
union all
select 'product_missing_category', p.product_id
from {{ ref('stg_products') }} p where p.category_pt is null
union all
select 'closed_deal_seller_never_in_seller_table', d.mql_id
from {{ ref('stg_closed_deals') }} d left join {{ ref('stg_sellers') }} s using (seller_id)
where s.seller_id is null
union all
select 'closed_deal_without_lead', d.mql_id
from {{ ref('stg_closed_deals') }} d left join {{ ref('stg_leads') }} l using (mql_id)
where l.mql_id is null
union all
select 'closed_deal_won_before_first_contact', d.mql_id
from {{ ref('stg_closed_deals') }} d join {{ ref('stg_leads') }} l using (mql_id)
where cast(d.won_at as date) < l.first_contact_date
