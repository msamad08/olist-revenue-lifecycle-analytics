-- Orders whose status disagrees with their timestamps (order system vs. logistics system)
select order_id, order_status, purchased_at, approved_at, shipped_at, delivered_at, issue_type
from (
    select *,
        case
            when order_status = 'delivered' and delivered_at is null   then 'delivered_status_no_delivery_date'
            when order_status <> 'delivered' and delivered_at is not null
                 and order_status <> 'canceled'                        then 'delivery_date_but_not_delivered'
            when order_status = 'canceled' and delivered_at is not null then 'canceled_after_delivery'
            when approved_at < purchased_at                            then 'approved_before_purchase'
            when delivered_at < shipped_at                             then 'delivered_before_shipped'
            when shipped_at < purchased_at                             then 'shipped_before_purchase'
        end as issue_type
    from {{ ref('stg_orders') }}
)
where issue_type is not null
