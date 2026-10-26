with source as (
    select * from {{ source('erp', 'promotions') }}
),

renamed as (
    select
        upper(trim(promo_code))     as promo_code,
        trim(promo_name)            as promo_name,
        upper(trim(sku))            as sku,
        start_date,
        end_date,
        discount_pct,
        _loaded_at
    from source
)

select * from renamed
