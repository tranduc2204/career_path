select
    order_id,
    line_no,
    product_id,
    quantity,
    {{ cents_to_dollars('unit_price_cents') }}      as unit_price,
    _loaded_at
from {{ source('raw', 'order_items') }}
