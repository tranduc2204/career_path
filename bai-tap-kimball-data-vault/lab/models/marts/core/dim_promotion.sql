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

