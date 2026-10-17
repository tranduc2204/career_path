select
    product_id,
    {{ clean_string('product_name') }}              as product_name,
    {{ clean_string('category') }}                  as category,
    {{ cents_to_dollars('list_price_cents') }}      as list_price,
    _loaded_at
from {{ source('raw', 'products') }}
