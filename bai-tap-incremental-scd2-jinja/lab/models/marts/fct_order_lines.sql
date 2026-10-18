

with order_line as (
    select 
        order_id,
        line_no,
        product_id,
        quantity,
        unit_price,
        _loaded_at
    from {{ ref ('stg_order_items') }}
), orders as (
    select 
        order_id,
        customer_id,
        order_date,
        order_status,
        _loaded_at
    from {{ ref ('stg_orders') }}
)
select 
    ol.order_id, 
    ol.line_no,
    ol.product_id,
    ol.quantity,
    ol.unit_price,
    o.order_date,
    o.customer_id, 
    o.order_status,
    ol.quantity * ol.unit_price as line_amount
from order_line ol 
left join orders o on ol.order_id = o.order_id

