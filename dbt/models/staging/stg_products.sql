select
    p.product_id,
    p.product_category_name                                        as category_pt,
    coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as category
from {{ source('raw', 'products') }} p
left join {{ source('raw', 'category_translation') }} t
    on p.product_category_name = t.product_category_name
