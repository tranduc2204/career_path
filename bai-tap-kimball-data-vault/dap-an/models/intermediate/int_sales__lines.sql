-- Gộp dòng bán của 2 hệ thống (website/app và POS) về cùng một hình dạng.
-- Grain: 1 dòng đơn / dòng hoá đơn. Giữ cả đơn huỷ (cờ is_cancelled) để mart tự quyết định.
with voucher_totals as (
    select order_number, sum(discount_amount) as order_discount_total
    from {{ ref('stg_shop__order_vouchers') }}
    group by order_number
),

shop_lines as (
    select
        'shop'                                  as source_system,
        l.order_number,
        l.line_no,
        l.sku,
        l.quantity,
        l.unit_price,
        l.quantity * l.unit_price               as gross_amount,
        o.order_ts,
        o.order_date,
        o.customer_code,
        o.channel,
        o.payment_method,
        o.is_gift,
        cast(null as varchar)                   as store_code,
        o.order_status = 'cancelled'            as is_cancelled,
        coalesce(v.order_discount_total, 0)     as order_discount_total,
        o.shipping_fee
    from {{ ref('stg_shop__order_lines') }} as l
    inner join {{ ref('stg_shop__orders') }} as o using (order_number)
    left join voucher_totals as v using (order_number)
),

pos_lines as (
    select
        'pos'                                   as source_system,
        receipt_no                              as order_number,
        line_no,
        sku,
        quantity,
        unit_price,
        quantity * unit_price                   as gross_amount,
        sale_ts                                 as order_ts,
        sale_date                               as order_date,
        customer_code,
        'store'                                 as channel,
        payment_method,
        false                                   as is_gift,
        store_code,
        false                                   as is_cancelled,
        cast(0 as bigint)                       as order_discount_total,
        cast(0 as bigint)                       as shipping_fee
    from {{ ref('stg_pos__sales') }}
)

select * from shop_lines
union all
select * from pos_lines
