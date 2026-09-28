-- A lead cannot be activated without being won, or retained without being activated
select mql_id from {{ ref('fct_lead_funnel') }}
where (is_activated and not is_won) or (is_retained and not is_activated)
