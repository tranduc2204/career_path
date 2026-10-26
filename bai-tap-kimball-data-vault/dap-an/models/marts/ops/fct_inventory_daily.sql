-- PERIODIC SNAPSHOT. GRAIN: 1 sản phẩm × 1 kho × 1 ngày, DÀY ĐẶC (ngày không có biến động vẫn có dòng).
-- quantity_on_hand là measure BÁN CỘNG (semi-additive): cộng theo sản phẩm/kho được, KHÔNG cộng theo ngày.
-- Dựng lại toàn bộ mỗi lần chạy → điều chỉnh lùi ngày (late-arriving) tự được tính vào các ngày cũ.
with days as (
    select date_key, full_date
    from {{ ref('dim_date') }}
    where full_date between (select min(movement_date) from {{ ref('stg_wms__stock_movements') }})
                        and {{ business_date() }}
),

grid as (
    select d.date_key, d.full_date, p.sku, w.location_code as warehouse_code
    from days as d
    cross join (select sku from {{ ref('stg_erp__products') }}) as p
    cross join (select location_code from {{ ref('stg_erp__locations') }} where location_type = 'warehouse') as w
),

daily as (
    select
        movement_date,
        sku,
        warehouse_code,
        sum(case when qty_change > 0 then qty_change else 0 end)    as quantity_in,
        sum(case when qty_change < 0 then -qty_change else 0 end)   as quantity_out,
        sum(qty_change)                                             as net_change
    from {{ ref('stg_wms__stock_movements') }}
    group by movement_date, sku, warehouse_code
),

filled as (
    select
        g.*,
        coalesce(d.quantity_in, 0)      as quantity_in,
        coalesce(d.quantity_out, 0)     as quantity_out,
        coalesce(d.net_change, 0)       as net_change
    from grid as g
    left join daily as d
        on  d.movement_date = g.full_date
        and d.sku = g.sku
        and d.warehouse_code = g.warehouse_code
)

select
    f.date_key                                                      as snapshot_date_key,
    p.product_key,
    l.location_key                                                  as warehouse_location_key,
    sum(f.net_change) over (
        partition by f.sku, f.warehouse_code
        order by f.full_date
        rows between unbounded preceding and current row
    )                                                               as quantity_on_hand,
    f.quantity_in,
    f.quantity_out
from filled as f
inner join {{ ref('dim_product') }} as p on p.sku = f.sku
inner join {{ ref('dim_location') }} as l on l.location_code = f.warehouse_code
