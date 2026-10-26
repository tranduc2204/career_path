


with order_info as (
    select *
    from {{ ref('fct_orders') }}
), customer_info as (
    select *
    from {{ ref('dim_customers') }}
    order by customer_id
)
select 
    ord.order_id, ord.order_date, ord.customer_id, ord.order_status,
    ord.amount, 
    coalesce(cst.customer_sk,'-1') as customer_sk,
    coalesce(cst.city, 'Unknown') as customer_city_at_order,
    cst.city as customer_city_at_order,
    cst.tier as customer_tier_at_order
from order_info ord 
left join customer_info cst 
    on ord.customer_id = cst.customer_id
    and cast(ord.order_date as timestamp) >= cst.valid_from
    and cast(ord.order_date as timestamp) <  cst.valid_to

 














