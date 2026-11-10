with fct_orders as (
    select distinct order_number            -- rút về grain 1 đơn
    from {{ ref('fct_sales') }}
), order_voucher as (
    select order_number, voucher_code, sum(discount_amount) as discount_amount
    from {{ ref('stg_shop__order_vouchers') }}
    group by order_number, voucher_code
), weighted as (
    select *,
        discount_amount
          / nullif(sum(discount_amount) over (partition by order_number), 0) as weighting_factor
    from order_voucher
)
select
    o.order_number,
    case when w.order_number is null then '-2'          -- đơn không voucher
         else coalesce(v.voucher_key, '-1') end          as voucher_key,   -- voucher lạ → UNKNOWN
    cast(coalesce(w.discount_amount, 0) as bigint)       as voucher_discount_amount,
    coalesce(w.weighting_factor, 1.0)                    as weighting_factor
from fct_orders o
left join weighted w        on o.order_number = w.order_number
left join {{ ref('dim_voucher') }} v on v.voucher_code = w.voucher_code
