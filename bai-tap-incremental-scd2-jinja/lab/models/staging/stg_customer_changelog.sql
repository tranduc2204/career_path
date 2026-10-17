select
    customer_id,
    op,
    trim(full_name)                         as full_name,
    nullif(lower(trim(email)), '')          as email,
    trim(city)                              as city,
    trim(tier)                              as tier,
    changed_at,
    _loaded_at
from {{ source('raw', 'customer_changelog') }}
