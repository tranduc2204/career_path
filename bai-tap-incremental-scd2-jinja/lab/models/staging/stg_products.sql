-- TODO J1: thay phép chia cents bằng macro cents_to_dollars()
-- TODO J2: thay trim/nullif bằng macro clean_string()
select
    product_id,
    nullif(trim(product_name), '')          as product_name,
    nullif(trim(category), '')              as category,
    round(list_price_cents / 100.0, 2)      as list_price,
    _loaded_at
from {{ source('raw', 'products') }}
