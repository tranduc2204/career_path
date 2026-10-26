with source as (
    select * from {{ source('erp', 'categories') }}
),

renamed as (
    select
        upper(trim(category_code))  as category_code,
        trim(category_name)         as category_name,
        upper(trim(parent_code))    as parent_code,
        _loaded_at
    from source
)

select * from renamed
