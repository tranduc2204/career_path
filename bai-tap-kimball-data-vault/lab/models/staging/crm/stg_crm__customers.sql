-- Giữ MỌI file (lịch sử). 1 dòng = 1 khách × 1 file ngày.
with source as (
    select * from {{ source('crm', 'customers') }}
),

renamed as (
    select
        upper(trim(customer_code))          as customer_code,
        trim(full_name)                     as full_name,
        nullif(lower(trim(email)), '')      as email,
        trim(city)                          as city,
        trim(loyalty_tier)                  as loyalty_tier,
        _extract_date                       as extract_date,
        _loaded_at
    from source
)

select * from renamed
