-- fct_sales dựng từ VAULT. Phải ra ĐÚNG Y HỆT fct_sales của tuần 4.
-- Nhìn số lượng join cần thiết: đây là cái giá của mô hình "chuẩn hoá cao" khi đem ra cho BI dùng.
with lines as (
    select
        l.ORDER_HK,
        o.order_number,
        l.line_no,
        p.sku,
        l.quantity,
        l.unit_price,
        l.quantity * l.unit_price   as gross_amount
    from {{ ref('nh_link_order_line') }} as l
    inner join {{ ref('hub_order') }} as o using (ORDER_HK)
    inner join {{ ref('hub_product') }} as p using (PRODUCT_HK)
),

shop_header as (
    select ORDER_HK, channel, payment_method, is_gift, shipping_fee, order_status, order_ts
    from {{ ref('sat_order_shop') }}
    qualify row_number() over (partition by ORDER_HK order by LOAD_DATETIME desc) = 1
),

pos_header as (
    select ORDER_HK, store_code, payment_method, sale_ts
    from {{ ref('sat_order_pos') }}
    qualify row_number() over (partition by ORDER_HK order by LOAD_DATETIME desc) = 1
),

order_customer as (
    select l.ORDER_HK, h.customer_code
    from {{ ref('link_order_customer') }} as l
    inner join {{ ref('hub_customer') }} as h using (CUSTOMER_HK)
),

discounts as (
    select ORDER_HK, sum(discount_amount) as order_discount_total
    from {{ ref('nh_link_order_voucher') }}
    group by ORDER_HK
),

unified as (
    select
        l.*,
        case when sh.ORDER_HK is not null then 'shop' else 'pos' end      as source_system,
        coalesce(sh.order_ts, ph.sale_ts)                                   as order_ts,
        case when sh.ORDER_HK is not null then sh.channel else 'store' end as channel,
        coalesce(sh.payment_method, ph.payment_method)                      as payment_method,
        coalesce(sh.is_gift, false)                                         as is_gift,
        ph.store_code,
        nullif(oc.customer_code, '-2')                                      as customer_code,
        coalesce(d.order_discount_total, 0)                                 as order_discount_total,
        coalesce(sh.shipping_fee, 0)                                        as shipping_fee,
        coalesce(sh.order_status = 'cancelled', false)                      as is_cancelled
    from lines as l
    left join shop_header as sh using (ORDER_HK)
    left join pos_header as ph using (ORDER_HK)
    left join order_customer as oc using (ORDER_HK)
    left join discounts as d using (ORDER_HK)
),

shares as (
    select
        *,
        sum(gross_amount) over (partition by order_number)          as order_gross_amount,
        line_no = max(line_no) over (partition by order_number)     as is_last_line
    from unified
    where not is_cancelled
),

parts as (
    select
        *,
        case when not is_last_line
             then round(order_discount_total * gross_amount / order_gross_amount) end   as discount_part,
        case when not is_last_line
             then round(shipping_fee * gross_amount / order_gross_amount) end           as shipping_part
    from shares
),

allocated as (
    select
        *,
        cast(coalesce(discount_part,
                      order_discount_total - coalesce(sum(discount_part) over (partition by order_number), 0))
             as bigint)                                                                  as discount_allocated,
        cast(coalesce(shipping_part,
                      shipping_fee - coalesce(sum(shipping_part) over (partition by order_number), 0))
             as bigint)                                                                  as shipping_fee_allocated
    from parts
)

select
    {{ date_key('a.order_ts') }}                                                    as order_date_key,
    coalesce(c.customer_key, '-1')                                                  as customer_key,
    {{ dbt_utils.generate_surrogate_key(['a.sku']) }}                               as product_key,
    {{ dbt_utils.generate_surrogate_key(['a.channel', 'a.payment_method', 'a.is_gift']) }}  as order_profile_key,
    case when a.store_code is null then '-2'
         else {{ dbt_utils.generate_surrogate_key(['a.store_code']) }} end          as store_location_key,
    a.source_system,
    a.order_number,
    a.line_no,
    a.order_ts,
    a.quantity,
    a.unit_price,
    a.gross_amount,
    a.discount_allocated,
    a.shipping_fee_allocated,
    a.gross_amount - a.discount_allocated + a.shipping_fee_allocated               as net_amount
from allocated as a
left join {{ ref('dim_customer_dv') }} as c
    on  c.customer_code = a.customer_code
    and a.order_ts >= c.valid_from
    and a.order_ts <  c.valid_to
