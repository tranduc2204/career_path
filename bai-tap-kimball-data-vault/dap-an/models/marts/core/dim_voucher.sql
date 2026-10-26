select
    {{ dbt_utils.generate_surrogate_key(['voucher_code']) }}   as voucher_key,
    voucher_code,
    voucher_type,
    voucher_name
from {{ ref('stg_erp__vouchers') }}

union all
select '-1', '-1', 'unknown', 'Không xác định'
union all
select '-2', 'KHONG_VOUCHER', 'none', 'Không dùng voucher'
