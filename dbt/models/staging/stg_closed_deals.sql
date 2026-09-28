select
    mql_id,
    seller_id,
    sdr_id,
    sr_id,
    cast(won_date as timestamp)                                   as won_at,
    coalesce(nullif(business_segment, ''), 'unknown')             as business_segment,
    coalesce(nullif(lead_type, ''), 'unknown')                    as lead_type,
    coalesce(nullif(business_type, ''), 'unknown')                as business_type,
    try_cast(declared_monthly_revenue as double)                  as declared_monthly_revenue
from {{ source('raw', 'closed_deals') }}
