-- 2 cách đọc doanh thu theo voucher:
--   weighted_net_amount: chia doanh thu theo trọng số → cộng mọi voucher = đúng tổng doanh thu.
--   impact_net_amount:   doanh thu của các đơn CÓ dùng voucher đó (không chia) → cộng lại sẽ VƯỢT tổng (đếm trùng).
select
    dv.voucher_code,
    dv.voucher_name,
    count(distinct f.order_number)                  as order_count,
    sum(f.net_amount * b.weighting_factor)          as weighted_net_amount,
    sum(f.net_amount)                               as impact_net_amount
from {{ ref('fct_sales') }} as f
inner join {{ ref('bridge_order_voucher') }} as b using (order_number)
inner join {{ ref('dim_voucher') }} as dv using (voucher_key)
group by dv.voucher_code, dv.voucher_name
