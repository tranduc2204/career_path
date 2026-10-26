-- SCD Type 1: luôn là thuộc tính hiện tại (đổi danh mục / giá niêm yết thì GHI ĐÈ, lịch sử bán hàng tự "chuyển" theo).
with products as (
    select * from {{ ref('stg_erp__products') }}
),

categories as (
    select * from {{ ref('int_category__paths') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['p.sku']) }}  as product_key,
    p.sku,
    p.product_name,
    p.brand,
    p.list_price,
    p.category_code,
    c.category_name,
    c.category_level,
    c.category_l1_code,
    c.category_l1_name
from products as p
left join categories as c using (category_code)

union all

select '-1', '-1', 'Không xác định', 'Không xác định', null, '-1', 'Không xác định', null, '-1', 'Không xác định'
