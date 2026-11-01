
{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='order_date',
    )
}}

with orders as (
    select *
    from {{ ref('int_orders') }}

),
{% if is_incremental() %}
list_new_orders as(
    select distinct order_date
    from orders
    where _loaded_at > (select max(max_loaded_at) from {{ this }})
    {% if var('backfill_start', none )%}
        or order_date between '{{ var("backfill_start") }}' and ' {{ var("backfill_end") }} '
    {% endif %}
),
{% endif %}

result as (
    select *
    from orders
    {% if is_incremental() %}   
        where order_date in (select order_date from list_new_orders)
    {% endif %}
)
select 
    order_date,
  
    count (case when is_revenue_order then 1 end) as order_count,
    coalesce(sum(case when is_revenue_order then amount end), 0) as revenue,
    max(_loaded_at) as max_loaded_at
from result
group by order_date