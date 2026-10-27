select
    cua_hang,
    ngay,
    avg(doanh_thu) over w as tb_7_dong,
    count(*)       over w as so_dong
from doanh_thu_ngay
window w as (
    partition by cua_hang
    order by ngay
    rows between 6 preceding and current row
)
