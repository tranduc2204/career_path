{% snapshot snap_products %}

{{
    config(
        target_schema='snapshot',
        unique_key='product_id',
        strategy='check',
        check_cols=['product_name', 'category', 'list_price_cents'],
    )
}}

select product_id, product_name, category, list_price_cents ,
_loaded_at
from {{ source('raw','products') }}

{% endsnapshot %}