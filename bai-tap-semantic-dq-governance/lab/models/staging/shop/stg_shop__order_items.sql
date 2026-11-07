select
    cast(order_id as varchar) || '-' || cast(line_no as varchar)  as order_item_id,
    order_id,
    line_no,
    product_id,
    cast(quantity as bigint)                as quantity,
    cast(unit_price as bigint)              as unit_price,
    cast(unit_cost as bigint)               as unit_cost,
    cast(quantity as bigint) * unit_price   as line_amount,
    cast(quantity as bigint) * unit_cost    as line_cost,
    _loaded_at
from {{ source('shop', 'order_items') }}
