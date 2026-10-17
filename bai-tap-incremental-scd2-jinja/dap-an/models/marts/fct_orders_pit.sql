-- S6 — point-in-time join: thuộc tính khách hàng TẠI thời điểm đặt đơn
with orders as (
    select * from {{ ref('fct_orders') }}
),

customers as (
    select * from {{ ref('dim_customers') }}
    where customer_id <> -1
)

select
    o.order_id,
    o.order_date,
    o.customer_id,
    o.order_status,
    o.amount,
    coalesce(c.customer_sk, '-1')       as customer_sk,
    coalesce(c.city, 'Unknown')         as customer_city_at_order,
    coalesce(c.tier, 'Unknown')         as customer_tier_at_order
from orders o
left join customers c
    on  o.customer_id = c.customer_id
    and cast(o.order_date as timestamp) >= c.valid_from
    and cast(o.order_date as timestamp) <  c.valid_to
