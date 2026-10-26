-- 1 dòng = 1 dòng hoá đơn. Khách vãng lai: customer_code = null.
with source as (
    select * from {{ source('pos', 'sales') }}
),

renamed as (
    select
        upper(trim(receipt_no))                     as receipt_no,
        upper(trim(store_code))                     as store_code,
        nullif(upper(trim(customer_code)), '')      as customer_code,
        lower(payment_method)                       as payment_method,
        sale_ts,
        cast(sale_ts as date)                       as sale_date,
        line_no,
        upper(trim(sku))                            as sku,
        quantity,
        cast(unit_price as bigint)                  as unit_price,
        _loaded_at
    from source
)

select * from renamed
