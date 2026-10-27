select
    cua_hang,
    ngay,
    doanh_thu / sum(doanh_thu) over thang_ca as ty_trong_thang,
    sum(doanh_thu) over thang_luy_ke / sum(doanh_thu) over thang_ca as ty_trong_luy_ke
from doanh_thu_ngay
window
    -- không ORDER BY → khung là cả partition
    thang_ca as (partition by cua_hang, date_trunc('month', ngay)),
    thang_luy_ke as (
        partition by cua_hang, date_trunc('month', ngay)
        order by ngay
        rows between unbounded preceding and current row
    )
