-- B6 — fact mức dòng đơn. Grain: 1 dòng = 1 (order_id, line_no)
with items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select * from {{ ref('stg_orders') }}
)

select
    items.order_id,
    items.line_no,
    orders.order_date,
    orders.customer_id,
    orders.order_status,
    items.product_id,
    items.quantity,
    items.unit_price,
    items.quantity * items.unit_price           as line_amount
from items
left join orders using (order_id)
