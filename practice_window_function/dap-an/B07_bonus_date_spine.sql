-- B07 bonus · Cách 2: date spine + ROWS (dùng khi warehouse không có RANGE ... INTERVAL)
-- Ý tưởng: "lấp đầy" mọi ngày (ngày nghỉ = 0) → khi ấy 1 dòng = 1 ngày, nên ROWS 6 PRECEDING
-- đúng bằng 7 ngày lịch. Cuối cùng chỉ giữ lại các ngày có dòng thật.
-- Trong dbt: dbt_utils.date_spine thay cho generate_series.
with spine as (
    select c.cua_hang, s.ngay::date as ngay
    from (select cua_hang, min(ngay) as tu, max(ngay) as den from doanh_thu_ngay group by 1) c,
         generate_series(c.tu, c.den, interval 1 day) as s(ngay)
),
day_du as (
    select
        s.cua_hang,
        s.ngay,
        coalesce(d.doanh_thu, 0) as doanh_thu,
        (d.ngay is not null)::int as co_ban
    from spine s
    left join doanh_thu_ngay d using (cua_hang, ngay)
),
cua_so as (
    select
        *,
        sum(doanh_thu) over w as tong_7_ngay,
        sum(co_ban)    over w as so_ngay_co_ban
    from day_du
    window w as (partition by cua_hang order by ngay rows between 6 preceding and current row)
)
select cua_hang, ngay, tong_7_ngay, so_ngay_co_ban
from cua_so
where co_ban = 1
