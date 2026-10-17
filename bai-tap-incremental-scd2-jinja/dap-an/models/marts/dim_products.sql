-- B6 — dimension sản phẩm (trạng thái hiện tại, SCD1)
select
    product_id,
    product_name,
    category,
    list_price
from {{ ref('stg_products') }}
