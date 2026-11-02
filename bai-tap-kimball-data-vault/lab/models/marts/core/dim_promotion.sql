with promotion_info as (
    select *
    from {{ ref('stg_erp__promotions') }}
)
select
    {{ dbt_utils.generate_surrogate_key(['promo_code']) }} as promotion_key,
    promo_code,
    promo_name, 
    discount_pct,
    start_date,
    end_date
from promotion_info

union all

select 
    -1 as promotion_key,
    -1 as promo_code,
    'UNKNOWN' as promo_name,
    0 as discount_pct,
    null as start_date,
    null as end_date