with source as (
    select * from {{ source('shop', 'order_vouchers') }}
),

renamed as (
    select
        upper(trim(order_number))       as order_number,
        upper(trim(voucher_code))       as voucher_code,
        cast(discount_amount as bigint) as discount_amount,
        _loaded_at
    from source
)

select * from renamed
