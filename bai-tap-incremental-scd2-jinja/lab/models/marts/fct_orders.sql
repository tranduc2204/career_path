{{
    config (
        materialized='incremental',
        incremental_strategy='merge', 
        unique_key='order_id',
    )
}}
select *
from {{ ref('stg_orders') }}

{% if is_incremental() %}
    where _loaded_at > (select max(_loaded_at) from {{ this }})
{% endif %}
