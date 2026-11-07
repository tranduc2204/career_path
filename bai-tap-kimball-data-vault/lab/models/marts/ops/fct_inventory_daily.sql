



with date_info as (
    select date_key, full_date
    from {{ ref('dim_date') }}
    where full_date between 
                (select min(movement_date) from {{ ref('stg_wms__stock_movements') }})
              and  (select max(movement_date) from {{ ref('stg_wms__stock_movements') }} )
),grid as (                   
    select d.date_key, d.full_date, p.sku, w.location_code as warehouse_code
    from date_info as d
    cross join (select sku from {{ ref('stg_erp__products') }}) as p
    cross join (select location_code from {{ ref('stg_erp__locations') }} where location_type = 'warehouse') as w
), daily as (
    select 
        movement_date, 
        sku,
        warehouse_code,
        sum(case when qty_change > 0 then qty_change else 0 end)    as quantity_in,
        sum(case when qty_change < 0 then -qty_change else 0 end)   as quantity_out,
        sum(qty_change)   as net_change
    from {{ ref('stg_wms__stock_movements') }}
    group by movement_date, 
        sku,
        warehouse_code
)
, result as (
select g.*,
        coalesce(d.quantity_in, 0)  as quantity_in,
        coalesce(d.quantity_out, 0) as quantity_out,
        coalesce(d.net_change, 0)   as net_change

from grid as g
left join daily d
    on d.movement_date = g.full_date
    and g.sku = d.sku
    and g.warehouse_code = d.warehouse_code
{# from {{ref('stg_wms__stock_movements')}} #}
)
select
    f.date_key                                                      as snapshot_date_key,
    p.product_key,
    l.location_key                                                  as warehouse_location_key,
    sum(f.net_change) over (
        partition by f.sku, f.warehouse_code
        order by f.full_date asc
        rows between unbounded preceding and current row
    )                                                               as quantity_on_hand,
    f.quantity_in,
    f.quantity_out
from result as f
inner join {{ ref('dim_product') }} as p on p.sku = f.sku
inner join {{ ref('dim_location') }} as l on l.location_code = f.warehouse_code






