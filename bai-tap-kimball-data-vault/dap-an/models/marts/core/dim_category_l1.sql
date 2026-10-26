-- Shrunken dimension: danh mục cấp 1. Cột trùng tên + giá trị với dim_product.category_l1_* (conformed).
select
    {{ dbt_utils.generate_surrogate_key(['category_l1_code']) }}   as category_l1_key,
    category_l1_code,
    category_l1_name
from {{ ref('int_category__paths') }}
where category_level = 1
