-- Grain: 1 dòng / đơn hàng (mọi trạng thái, kể cả cancelled).
-- G3: sum(bigint) trên DuckDB trả về HUGEINT (int128) → ép về bigint để khớp contract.
with items as (
    select
        order_id,
        count(*)          as item_lines,
        cast(sum(quantity) as bigint)     as item_quantity,
        cast(sum(line_amount) as bigint)  as items_amount,
        cast(sum(line_cost) as bigint)    as items_cost
    from {{ ref('stg_shop__order_items') }}
    group by order_id
)
select
    o.order_id,
    o.customer_id,
    o.session_id,
    o.order_ts,
    o.order_date,
    o.channel,
    o.utm_source,
    o.payment_method,
    o.status,
    o.status = 'cancelled'               as is_cancelled,
    coalesce(i.item_lines, 0)            as item_lines,
    coalesce(i.item_quantity, 0)         as item_quantity,
    coalesce(i.items_amount, 0)          as items_amount,
    coalesce(i.items_cost, 0)            as items_cost,
    o.shipping_fee
from {{ ref('stg_shop__orders') }} o
left join items i using (order_id)
