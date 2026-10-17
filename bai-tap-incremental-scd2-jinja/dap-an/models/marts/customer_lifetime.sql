-- B7 — giá trị vòng đời khách hàng, chỉ tính đơn có doanh thu (quy tắc ở int_orders)
select
    customer_id,
    count(*)                    as order_count,
    sum(amount)                 as lifetime_value,
    min(order_date)             as first_order_date,
    max(order_date)             as last_order_date
from {{ ref('int_orders') }}
where is_revenue_order
group by customer_id
