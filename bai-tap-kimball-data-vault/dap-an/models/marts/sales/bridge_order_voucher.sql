-- Bridge cho dimension nhiều giá trị: 1 đơn có 0..n voucher.
-- weighting_factor = phần voucher đó chiếm trong tổng giảm giá của đơn → tổng trọng số mỗi đơn = 1.
-- Đơn không dùng voucher → 1 dòng trỏ tới thành viên '-2' (KHONG_VOUCHER), trọng số 1, để join không làm rơi doanh thu.
with vouchers as (
    select
        order_number,
        voucher_code,
        discount_amount,
        sum(discount_amount) over (partition by order_number)  as order_discount_total
    from {{ ref('stg_shop__order_vouchers') }}
),

sold_orders as (
    select distinct order_number from {{ ref('fct_sales') }}
)

select
    o.order_number,
    dv.voucher_key,
    v.discount_amount                                           as voucher_discount_amount,
    v.discount_amount * 1.0 / v.order_discount_total            as weighting_factor
from sold_orders as o
inner join vouchers as v using (order_number)
inner join {{ ref('dim_voucher') }} as dv using (voucher_code)

union all

select
    o.order_number,
    '-2'                    as voucher_key,
    cast(0 as bigint)       as voucher_discount_amount,
    1.0                     as weighting_factor
from sold_orders as o
where o.order_number not in (select order_number from vouchers)
