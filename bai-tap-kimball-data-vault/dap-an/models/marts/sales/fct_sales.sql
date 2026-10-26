-- Transaction fact. GRAIN: 1 dòng = 1 dòng đơn online hoặc 1 dòng hoá đơn POS ĐÃ BÁN (đơn huỷ không có mặt).
-- Voucher và phí ship nằm ở cấp ĐẦU ĐƠN → phân bổ xuống dòng theo tỷ trọng gross_amount,
-- làm tròn tới đồng, dòng có line_no lớn nhất nhận phần dư → tổng các dòng luôn khớp đầu đơn.
with lines as (
    select * from {{ ref('int_sales__lines') }}
    where not is_cancelled
),

shares as (
    select
        *,
        sum(gross_amount) over (partition by order_number)          as order_gross_amount,
        line_no = max(line_no) over (partition by order_number)     as is_last_line
    from lines
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
    {{ date_key('a.order_date') }}                      as order_date_key,
    coalesce(c.customer_key, '-1')                      as customer_key,
    coalesce(p.product_key, '-1')                       as product_key,
    op.order_profile_key,
    coalesce(s.location_key, '-2')                      as store_location_key,
    -- degenerate dimensions: định danh giao dịch, không cần bảng dimension riêng
    a.source_system,
    a.order_number,
    a.line_no,
    a.order_ts,
    -- measures (cộng được theo mọi chiều)
    a.quantity,
    a.unit_price,
    a.gross_amount,
    a.discount_allocated,
    a.shipping_fee_allocated,
    a.gross_amount - a.discount_allocated + a.shipping_fee_allocated   as net_amount
from allocated as a
left join {{ ref('dim_customer') }} as c
    on  c.customer_code = a.customer_code
    and a.order_ts >= c.valid_from
    and a.order_ts <  c.valid_to
left join {{ ref('dim_product') }} as p
    on p.sku = a.sku
left join {{ ref('dim_order_profile') }} as op
    on  op.channel = a.channel
    and op.payment_method = a.payment_method
    and op.is_gift = a.is_gift
left join {{ ref('dim_location') }} as s
    on s.location_code = a.store_code
