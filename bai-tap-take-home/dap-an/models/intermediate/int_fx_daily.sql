-- Tỷ giá cho MỌI ngày lịch: ngày không có niêm yết (cuối tuần, lễ) dùng tỷ giá gần nhất trước đó. VND = 1.
with spine as (
    select cast(d as date) as rate_date
    from range(date '2026-08-01', cast('{{ var("as_of_date") }}' as date) + 1, interval 1 day) t(d)
),
usd as (
    select s.rate_date, 'USD' as currency, f.vnd_per_unit
    from spine s
    asof join {{ ref('stg_ref__fx_rates') }} f
      on f.currency = 'USD' and s.rate_date >= f.rate_date
)
select * from usd
union all
select rate_date, 'VND', cast(1 as decimal(12, 2)) from spine
