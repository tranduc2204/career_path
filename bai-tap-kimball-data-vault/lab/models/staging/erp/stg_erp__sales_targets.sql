with source as (
    select * from {{ source('erp', 'sales_targets') }}
),

renamed as (
    select
        target_month,                               -- ngày đầu tháng
        upper(trim(category_code))  as category_code,   -- luôn là danh mục cấp 1
        cast(target_amount as bigint) as target_amount,
        _loaded_at
    from source
)

select * from renamed
