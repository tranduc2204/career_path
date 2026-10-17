-- I3/I4/I7 — merge theo order_id, watermark theo _loaded_at, tự thêm cột mới
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_id',
    on_schema_change='append_new_columns'
) }}

select
    {{ dbt_utils.star(ref('stg_orders')) }},
    {{ days_between('order_date', 'updated_at') }} as days_to_last_update
from {{ ref('stg_orders') }}
{% if is_incremental() %}
where _loaded_at > (select max(_loaded_at) from {{ this }})
{% endif %}
