select product_id, product_name, category, brand, list_price
from {{ ref('stg_erp__products') }}
