-- Ở đây ta MUỐN gộp peer: số dư "tại thời điểm" gồm mọi giao dịch cùng thời điểm.
-- RANGE ... CURRENT ROW = tới hết peer cuối cùng. Viết tường minh dù trùng mặc định.
select
    giao_dich_id,
    sum(so_tien) over (
        partition by khach_hang_id
        order by thoi_diem
        range between unbounded preceding and current row
    ) as so_du
from giao_dich
