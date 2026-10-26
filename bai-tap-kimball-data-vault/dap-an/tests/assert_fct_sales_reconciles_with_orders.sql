-- Đối soát: với mỗi đơn online đã bán, tổng net_amount các dòng phải bằng đúng số tiền khách trả ở đầu đơn.
-- Sai lệch dù 1 đồng nghĩa là phân bổ voucher / phí ship bị lệch.
with fact as (
    select order_number, sum(net_amount) as fact_total
    from {{ ref('fct_sales') }}
    where source_system = 'shop'
    group by order_number
)

select o.order_number, o.total_amount, f.fact_total
from {{ ref('stg_shop__orders') }} as o
inner join fact as f using (order_number)
where o.total_amount <> f.fact_total
