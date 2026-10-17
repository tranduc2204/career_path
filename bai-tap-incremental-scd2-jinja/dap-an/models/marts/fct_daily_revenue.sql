-- I5 — delete+insert theo ngày: tính lại TOÀN BỘ các ngày bị ảnh hưởng.
-- I9/P4: backfill theo khoảng ngày bằng vars. P3/P6: quy tắc doanh thu lấy từ int_orders.
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='order_date'
) }}

with orders as (
    select * from {{ ref('int_orders') }}
),

{% if is_incremental() %}
affected_dates as (
    {% if var('backfill_start', none) is not none %}
    select distinct order_date from orders
    where order_date between '{{ var("backfill_start") }}' and '{{ var("backfill_end") }}'
    {% else %}
    select distinct order_date from orders
    where _loaded_at > (select max(max_loaded_at) from {{ this }})
    {% endif %}
),
{% endif %}

final as (
    select
        order_date,
        sum(case when is_revenue_order then 1 else 0 end)               as order_count,
        coalesce(sum(case when is_revenue_order then amount end), 0)    as revenue,
        max(_loaded_at)                                                 as max_loaded_at
    from orders
    {% if is_incremental() %}
    where order_date in (select order_date from affected_dates)
    {% endif %}
    group by order_date
)

select * from final
