select
    product_id,
    trim(product_name)          as product_name,
    category,
    brand,
    cast(list_price as bigint)  as list_price,
    cast(unit_cost as bigint)   as unit_cost,
    _loaded_at
from {{ source('erp', 'products') }}
