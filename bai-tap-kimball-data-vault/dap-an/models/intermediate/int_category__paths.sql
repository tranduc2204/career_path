-- Mỗi danh mục kèm cấp (level) và danh mục cấp 1 chứa nó. Cây không đều nên phải đệ quy.
with recursive paths as (
    select
        category_code,
        category_name,
        parent_code,
        1                   as category_level,
        category_code       as category_l1_code,
        category_name       as category_l1_name
    from {{ ref('stg_erp__categories') }}
    where parent_code is null

    union all

    select
        c.category_code,
        c.category_name,
        c.parent_code,
        p.category_level + 1,
        p.category_l1_code,
        p.category_l1_name
    from {{ ref('stg_erp__categories') }} as c
    inner join paths as p on c.parent_code = p.category_code
)

select * from paths
