-- Mỗi đơn trong bridge phải có tổng trọng số = 1, nếu không doanh thu theo voucher sẽ bị thừa/thiếu.
select order_number, sum(weighting_factor) as total_weight
from {{ ref('bridge_order_voucher') }}
group by order_number
having abs(sum(weighting_factor) - 1) > 0.000001
