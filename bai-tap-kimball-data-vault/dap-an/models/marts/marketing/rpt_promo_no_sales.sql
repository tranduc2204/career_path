-- Câu hỏi chỉ factless coverage trả lời được: "Sản phẩm nào ĐANG KM mà KHÔNG bán được cái nào?"
-- = (tập được KM) TRỪ (tập có bán). Chỉ xét tới ngày dữ liệu mới nhất.
select
    c.date_key,
    d.full_date,
    p.sku,
    p.product_name,
    pr.promo_code
from {{ ref('fct_promotion_coverage') }} as c
inner join {{ ref('dim_date') }} as d using (date_key)
inner join {{ ref('dim_product') }} as p using (product_key)
inner join {{ ref('dim_promotion') }} as pr using (promotion_key)
where d.full_date <= {{ business_date() }}
  and not exists (
      select 1
      from {{ ref('fct_sales') }} as s
      where s.product_key = c.product_key
        and s.order_date_key = c.date_key
  )
