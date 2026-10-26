-- Bridge cho cây phân cấp không đều (closure table): mọi cặp (tổ tiên, con cháu), kể cả chính nó (distance = 0).
-- Muốn cộng doanh số lên BẤT KỲ cấp nào: join fact → dim_product.category_code = descendant → group by ancestor.
with recursive closure as (
    select
        category_code   as ancestor_category_code,
        category_code   as descendant_category_code,
        0               as distance
    from {{ ref('stg_erp__categories') }}

    union all

    select
        c.ancestor_category_code,
        k.category_code,
        c.distance + 1
    from closure as c
    inner join {{ ref('stg_erp__categories') }} as k on k.parent_code = c.descendant_category_code
)

select
    c.ancestor_category_code,
    c.descendant_category_code,
    c.distance,
    a.category_level            as ancestor_level,
    d.category_level            as descendant_level
from closure as c
inner join {{ ref('int_category__paths') }} as a on a.category_code = c.ancestor_category_code
inner join {{ ref('int_category__paths') }} as d on d.category_code = c.descendant_category_code
