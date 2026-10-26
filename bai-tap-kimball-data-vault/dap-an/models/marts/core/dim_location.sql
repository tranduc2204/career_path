select
    {{ dbt_utils.generate_surrogate_key(['location_code']) }}  as location_key,
    location_code,
    location_name,
    location_type,
    city
from {{ ref('stg_erp__locations') }}

union all
select '-1', '-1', 'Không xác định', 'unknown', null
union all
select '-2', '-2', 'Không áp dụng (bán online)', 'not_applicable', null
