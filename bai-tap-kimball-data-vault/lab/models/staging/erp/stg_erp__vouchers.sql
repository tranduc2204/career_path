with source as (
    select * from {{ source('erp', 'vouchers') }}
),

renamed as (
    select
        upper(trim(voucher_code))   as voucher_code,
        lower(voucher_type)         as voucher_type,
        trim(voucher_name)          as voucher_name,
        _loaded_at
    from source
)

select * from renamed
