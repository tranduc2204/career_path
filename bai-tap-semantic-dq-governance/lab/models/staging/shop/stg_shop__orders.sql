select
    order_id,
    customer_id,
    session_id,
    order_ts,
    cast(order_ts as date)            as order_date,
    lower(channel)                    as channel,
    lower(utm_source)                 as utm_source,
    lower(payment_method)             as payment_method,
    cast(shipping_fee as bigint)      as shipping_fee,
    lower(status)                     as status,
    updated_at,
    _loaded_at
from {{ source('shop', 'orders') }}
