-- Khung có thể rỗng (ngày cuối dữ liệu) → SUM trả NULL → COALESCE về 0 theo yêu cầu.
select
    cua_hang,
    ngay,
    coalesce(sum(doanh_thu) over (
        partition by cua_hang
        order by ngay
        range between interval 1 day following and interval 7 days following
    ), 0) as tong_7_ngay_toi
from doanh_thu_ngay
