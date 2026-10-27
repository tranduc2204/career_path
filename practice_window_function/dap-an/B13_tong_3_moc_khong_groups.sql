-- Cách portable: gộp về 1 dòng / mốc → ROWS trên bảng đã gộp → join ngược lại.
with theo_moc as (
    select khach_hang_id, thoi_diem, sum(so_tien) as tien_moc
    from giao_dich
    group by khach_hang_id, thoi_diem
),
cua_so as (
    select
        khach_hang_id,
        thoi_diem,
        sum(tien_moc) over (
            partition by khach_hang_id
            order by thoi_diem
            rows between 2 preceding and current row
        ) as tong_3_moc
    from theo_moc
)
select g.giao_dich_id, c.tong_3_moc
from giao_dich g
join cua_so c using (khach_hang_id, thoi_diem)
