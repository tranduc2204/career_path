select
    cua_hang,
    ngay,
    sum(doanh_thu) over w as tong_7_ngay,
    count(*)       over w as so_ngay_co_ban
from doanh_thu_ngay
window w as (
    partition by cua_hang
    order by ngay
    range between interval 6 days preceding and current row
)
