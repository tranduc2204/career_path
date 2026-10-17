-- I3/I4/I7 — merge theo order_id, watermark theo _loaded_at, tự thêm cột mới.
-- P4: backfill theo khoảng order_date bằng vars khi nguồn sửa dữ liệu mà không đổi _loaded_at.
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
    {% if var('backfill_start', none) is not none %}
where order_date between '{{ var("backfill_start") }}' and '{{ var("backfill_end") }}'
    {% else %}
where _loaded_at > (select max(_loaded_at) from {{ this }})
    {% endif %}
{% endif %}
