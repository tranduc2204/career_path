select
    cua_hang,
    ngay,
    coalesce(sum(doanh_thu) over (
        partition by cua_hang, date_trunc('month', ngay)
        order by ngay
        rows between 1 following and unbounded following
    ), 0) as con_lai_trong_thang
from doanh_thu_ngay
