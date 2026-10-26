-- ACCUMULATING SNAPSHOT. GRAIN: 1 dòng = 1 đơn online (kể cả đơn huỷ), được CẬP NHẬT mỗi khi đơn qua mốc mới.
-- Mỗi mốc là một vai (role) của dim_date. Mốc chưa xảy ra → date_key = -1 ("Chưa xảy ra"), không để null.
-- Mốc lấy THỜI ĐIỂM XẢY RA SỚM NHẤT của sự kiện, bất kể sự kiện về kho theo thứ tự nào.
with orders as (
    select * from {{ ref('stg_shop__orders') }}
),

milestones as (
    select
        order_number,
        min(case when event_type = 'packed' then event_ts end)        as packed_at,
        min(case when event_type = 'shipped' then event_ts end)       as shipped_at,
        min(case when event_type = 'delivered' then event_ts end)     as delivered_at,
        min(case when event_type = 'returned' then event_ts end)      as returned_at,
        count(case when event_type = 'delivery_failed' then 1 end)    as failed_delivery_count,
        max(warehouse_code)                                           as warehouse_code
    from {{ ref('stg_wms__shipment_events') }}
    group by order_number
),

items as (
    select order_number, sum(quantity) as item_quantity
    from {{ ref('stg_shop__order_lines') }}
    group by order_number
)

select
    o.order_number,
    coalesce(c.customer_key, '-1')                      as customer_key,
    op.order_profile_key,
    coalesce(w.location_key, '-1')                      as warehouse_location_key,
    {{ date_key('o.order_ts') }}                        as order_date_key,
    {{ date_key('o.paid_at') }}                         as paid_date_key,
    {{ date_key('m.packed_at') }}                       as packed_date_key,
    {{ date_key('m.shipped_at') }}                      as shipped_date_key,
    {{ date_key('m.delivered_at') }}                    as delivered_date_key,
    {{ date_key('m.returned_at') }}                     as returned_date_key,
    {{ date_key('o.cancelled_at') }}                    as cancelled_date_key,
    case
        when o.cancelled_at is not null then 'cancelled'
        when m.returned_at is not null then 'returned'
        when m.delivered_at is not null then 'delivered'
        when m.shipped_at is not null then 'shipped'
        when m.packed_at is not null then 'packed'
        when o.paid_at is not null then 'paid'
        else 'placed'
    end                                                 as current_status,
    o.total_amount                                      as order_total_amount,
    i.item_quantity,
    coalesce(m.failed_delivery_count, 0)                as failed_delivery_count,
    date_diff('day', o.order_date, cast(m.shipped_at as date))      as days_to_ship,
    date_diff('day', o.order_date, cast(m.delivered_at as date))    as days_to_deliver
from orders as o
left join milestones as m using (order_number)
left join items as i using (order_number)
left join {{ ref('dim_customer') }} as c
    on  c.customer_code = o.customer_code
    and o.order_ts >= c.valid_from
    and o.order_ts <  c.valid_to
left join {{ ref('dim_order_profile') }} as op
    on  op.channel = o.channel
    and op.payment_method = o.payment_method
    and op.is_gift = o.is_gift
left join {{ ref('dim_location') }} as w
    on w.location_code = m.warehouse_code
