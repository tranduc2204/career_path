{% snapshot snap_products %}

{{
    config(
        target_schema='snapshot',
        unique_key='product_id',
        strategy='check',
        check_cols=['product_name', 'category', 'list_price'],
    )
}}

with product_info as (
select product_id, product_name, category, list_price_cents ,
_loaded_at
from {{ source('raw','products') }}
)
select 
product_id, product_name, category, list_price_cents  as list_price,
_loaded_at

from product_info
{% endsnapshot %}