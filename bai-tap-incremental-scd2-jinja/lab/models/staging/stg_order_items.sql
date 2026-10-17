-- TODO J1: thay phép chia cents bằng macro cents_to_dollars()
select
    order_id,
    line_no,
    product_id,
    quantity,
    round(unit_price_cents / 100.0, 2)      as unit_price,
    _loaded_at
from {{ source('raw', 'order_items') }}
