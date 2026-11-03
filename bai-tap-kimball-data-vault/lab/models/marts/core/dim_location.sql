with location_info as (
    select *
    from {{ ref('stg_erp__locations') }}
)
select 
    {{ dbt_utils.generate_surrogate_key(['location_code']) }} as location_key,
    location_code,
    location_name,
    location_type,
    city
from location_info

union all 

select 
    -1 as location_key, 
    -1 as location_code,
    'UNKNOWN' as location_name,
    'UNKNOWN' as location_type,
    'UNKNOWN' as city

union all

select 
    -2 as location_key, 
    -2 as location_code,
    'KHONG_VOUCHER' as location_name,
    'NULL' as location_type,
    'NULL' as city