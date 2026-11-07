select
    cast(spend_date as varchar) || '-' || lower(utm_source)  as ad_spend_id,
    spend_date,
    lower(utm_source)        as utm_source,
    cast(spend as bigint)    as spend,
    _loaded_at
from {{ source('mkt', 'ad_spend') }}
