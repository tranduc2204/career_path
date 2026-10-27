-- B02 · SỬA BUG: lũy kế giao dịch ví bị "nhảy cóc"         lý thuyết: 02 §3 (peer), 03 §1
-- Bảng: giao_dich(giao_dich_id, khach_hang_id, thoi_diem, so_tien)
--   - nhiều giao dịch của cùng khách có thể TRÙNG thoi_diem
--   - giao_dich_id KHÔNG tăng theo thời gian
--
-- Đồng nghiệp viết query dưới đây cho cột "số dư sau từng giao dịch" trên app.
-- Khách phàn nàn: 2 giao dịch liên tiếp hiển thị cùng một số dư.
--
-- Yêu cầu: luy_ke = tổng so_tien của khách tính tới VÀ GỒM giao dịch hiện tại, theo thứ tự
--          (thoi_diem, giao_dich_id) — giao dịch cùng thời điểm xếp theo giao_dich_id tăng dần.
-- Cột kết quả: giao_dich_id, luy_ke
-- Sau khi sửa, ghi 1 dòng comment giải thích vì sao query cũ sai.
-- Chấm:     python scripts/check.py B02

select
    giao_dich_id,
    sum(so_tien) over (partition by khach_hang_id order by thoi_diem) as luy_ke
from giao_dich
