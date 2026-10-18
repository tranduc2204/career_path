
with info_products as (
    select 
        product_id,
        product_name,
        category, 
        list_price

    from {{ ref('stg__products') }}
)
select 
        *
from info_products










