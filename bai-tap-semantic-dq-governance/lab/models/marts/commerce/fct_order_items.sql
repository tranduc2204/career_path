-- Grain: 1 dòng / dòng hàng. Mang xuống các khoá ngoại của đơn (customer_id, utm_source) và order_date
-- để fact này tự đứng được như một fact Kimball.
-- KHÔNG có trạng thái đơn: muốn lọc đơn huỷ thì đi qua entity order (fct_orders).
select
    i.order_item_id,
    i.order_id,
    i.line_no,
    i.product_id,
    o.customer_id,
    o.utm_source,
    o.order_date,
    i.quantity,
    i.unit_price,
    i.unit_cost,
    i.line_amount,
    i.line_cost
from {{ ref('stg_shop__order_items') }} i
join {{ ref('stg_shop__orders') }} o using (order_id)
