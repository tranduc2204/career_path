-- 1 dòng / chương trình khuyến mãi (bảng nguồn ở grain chương trình × sản phẩm).
select
    {{ dbt_utils.generate_surrogate_key(['promo_code']) }}     as promotion_key,
    promo_code,
    max(promo_name)                                             as promo_name,
    max(discount_pct)                                           as discount_pct,
    min(start_date)                                             as start_date,
    max(end_date)                                               as end_date
from {{ ref('stg_erp__promotions') }}
group by promo_code
