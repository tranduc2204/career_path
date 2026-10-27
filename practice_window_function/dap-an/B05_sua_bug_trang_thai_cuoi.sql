-- Bug gốc: LAST_VALUE với frame mặc định (… AND CURRENT ROW) → luôn trả chính dòng hiện tại.
select
    su_kien_id,
    don_id,
    first_value(trang_thai) over w as trang_thai_dau,
    last_value(trang_thai)  over w as trang_thai_cuoi
from su_kien_don
window w as (
    partition by don_id
    order by thoi_diem
    rows between unbounded preceding and unbounded following
)
