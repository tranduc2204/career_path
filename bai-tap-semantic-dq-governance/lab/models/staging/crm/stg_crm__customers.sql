select
    customer_id,
    full_name,
    lower(trim(email))   as email,
    phone,
    city,
    lower(segment)       as segment,
    birth_date,
    signup_date,
    updated_at,
    _loaded_at
from {{ source('crm', 'customers') }}
