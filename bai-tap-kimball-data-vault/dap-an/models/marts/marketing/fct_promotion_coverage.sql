-- FACTLESS FACT (coverage). GRAIN: 1 chương trình × 1 sản phẩm × 1 ngày được khuyến mãi.
-- Không có measure: bản thân việc dòng TỒN TẠI là thông tin ("sản phẩm X được KM vào ngày Y").
select
    d.date_key,
    p.product_key,
    pr.promotion_key
from {{ ref('stg_erp__promotions') }} as s
inner join {{ ref('dim_date') }} as d on d.full_date between s.start_date and s.end_date
inner join {{ ref('dim_product') }} as p on p.sku = s.sku
inner join {{ ref('dim_promotion') }} as pr on pr.promo_code = s.promo_code
