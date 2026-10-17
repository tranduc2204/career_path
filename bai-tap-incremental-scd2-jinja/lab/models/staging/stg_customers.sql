-- TODO J2: thay các biểu thức trim/lower/nullif bằng macro clean_string()
select
    customer_id,
    trim(full_name)                         as full_name,
    nullif(lower(trim(email)), '')          as email,
    trim(city)                              as city,
    trim(tier)                              as tier,
    updated_at,
    _loaded_at
from {{ source('raw', 'customers') }}
