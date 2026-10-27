-- Bug gốc: ORDER BY thoi_diem không unique + frame mặc định RANGE
--   → các giao dịch cùng thời điểm là "peer", cùng nhận tổng của cả nhóm.
-- Sửa: thêm tie-breaker để thứ tự unique, VÀ ghi rõ ROWS.
select
    giao_dich_id,
    sum(so_tien) over (
        partition by khach_hang_id
        order by thoi_diem, giao_dich_id
        rows between unbounded preceding and current row
    ) as luy_ke
from giao_dich
