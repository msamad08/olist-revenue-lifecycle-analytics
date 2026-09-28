select 'payment_reconciliation' as check_group, issue_type, count(*) as records
from {{ ref('dq_payment_reconciliation') }} group by 1, 2
union all
select 'order_lifecycle', issue_type, count(*) from {{ ref('dq_order_lifecycle_anomalies') }} group by 1, 2
union all
select 'referential_integrity', issue_type, count(*) from {{ ref('dq_orphan_keys') }} group by 1, 2
union all
select 'duplicates', 'possible_duplicate_checkout', count(*) from {{ ref('dq_possible_duplicate_orders') }}
union all
select 'volume', issue_type, count(*) from {{ ref('dq_volume_anomalies') }} group by 1, 2
order by 1, 3 desc
