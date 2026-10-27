select
    cua_hang,
    ngay,
    doanh_thu,
    sum(doanh_thu) over (
        partition by cua_hang
        order by ngay
        rows between unbounded preceding and current row
    ) as luy_ke
from doanh_thu_ngay
