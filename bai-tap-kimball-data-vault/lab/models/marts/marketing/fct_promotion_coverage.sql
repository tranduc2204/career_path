

select distinct 
    d.date_key, dp.product_key , pro.promotion_key 
from {{ ref('stg_erp__promotions') }} p
join {{ ref('dim_date') }} d 
    on d.full_date between p.start_date and p.end_date
join {{ ref('dim_product') }} dp 
    on p.sku = dp.sku
join {{ ref('dim_promotion') }} pro 
    on pro.promo_code = p.promo_code





























































