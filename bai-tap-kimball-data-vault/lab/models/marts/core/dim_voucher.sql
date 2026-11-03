with voucher_info as (
    select *
    from {{ ref('stg_erp__vouchers') }}
)
select 
    {{ dbt_utils.generate_surrogate_key(['voucher_code']) }} as voucher_key,
    voucher_code,
    voucher_type,
    voucher_name
from voucher_info

union all

select 
    -1 as voucher_key, 
    -1 as voucher_code,
    'UNKNOWN' as voucher_type,
    'UNKNOWN' as voucher_name

union all 

select 
    -2 as voucher_key, 
    'KHONG_VOUCHER' as voucher_code,
    'NULL' as voucher_type,
    'NULL' as voucher_name

