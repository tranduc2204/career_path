select
    giao_dich_id,
    sum(so_tien) over (
        partition by khach_hang_id
        order by thoi_diem
        groups between 2 preceding and current row
    ) as tong_3_moc
from giao_dich
