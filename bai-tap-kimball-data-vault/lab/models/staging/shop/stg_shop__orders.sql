with source as (
    select * from {{ source('shop', 'orders') }}
),

renamed as (
    select
        upper(trim(order_number))           as order_number,
        upper(trim(customer_code))          as customer_code,
        lower(channel)                      as channel,
        lower(payment_method)               as payment_method,
        is_gift,
        cast(shipping_fee as bigint)        as shipping_fee,     -- tiền VND: bigint để nhân/chia không tràn INT32
        cast(total_amount as bigint)        as total_amount,     -- số tiền khách phải trả cho cả đơn
        lower(status)                       as order_status,
        order_ts,
        cast(order_ts as date)              as order_date,
        paid_at,
        cancelled_at,
        updated_at,
        _loaded_at
    from source
)

select * from renamed
