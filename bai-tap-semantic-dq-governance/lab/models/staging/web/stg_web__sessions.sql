select
    session_id,
    customer_id,
    session_start,
    cast(session_start as date)  as session_date,
    lower(device)                as device,
    lower(utm_source)            as utm_source,
    landing_page,
    _loaded_at
from {{ source('web', 'sessions') }}
