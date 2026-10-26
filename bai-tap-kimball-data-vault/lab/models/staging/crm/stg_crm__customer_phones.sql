-- Giữ MỌI file. 1 dòng = 1 khách × 1 loại số × 1 file ngày.
with source as (
    select * from {{ source('crm', 'customer_phones') }}
),

renamed as (
    select
        upper(trim(customer_code))  as customer_code,
        lower(trim(phone_type))     as phone_type,
        trim(phone_number)          as phone_number,
        _extract_date               as extract_date,
        _loaded_at
    from source
)

select * from renamed
