{{
    config (
        materialized='incremental',
        incremental_strategy='merge', 
        unique_key='order_id',
  
    )
}}
with orders as (
select 
    {{ dbt_utils.star(ref('stg_orders')) }}
from {{ ref('stg_orders') }}
)
select *
from orders

{% if is_incremental() %}
    where _loaded_at > (select max(_loaded_at) from {{ this }})
{% endif %}
