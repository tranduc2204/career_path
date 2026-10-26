-- Doanh thu cộng dồn lên MỌI cấp của cây danh mục (kể cả cấp không có sản phẩm gắn trực tiếp).
with sales_by_leaf as (
    select p.category_code, sum(f.net_amount) as net_amount, sum(f.quantity) as quantity
    from {{ ref('fct_sales') }} as f
    inner join {{ ref('dim_product') }} as p using (product_key)
    group by p.category_code
)

select
    cat.category_code,
    cat.category_name,
    cat.category_level,
    coalesce(sum(s.net_amount), 0)      as net_amount,
    coalesce(sum(s.quantity), 0)        as quantity
from {{ ref('int_category__paths') }} as cat
left join {{ ref('bridge_category_hierarchy') }} as b
    on b.ancestor_category_code = cat.category_code
left join sales_by_leaf as s
    on s.category_code = b.descendant_category_code
group by cat.category_code, cat.category_name, cat.category_level
