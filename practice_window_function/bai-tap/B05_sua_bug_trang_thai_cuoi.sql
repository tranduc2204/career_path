-- B05 · SỬA BUG: "trạng thái cuối" của đơn sai               lý thuyết: 02 §5 (LAST_VALUE)
-- Bảng: su_kien_don(su_kien_id, don_id, thoi_diem, trang_thai)
--   - mỗi đơn có 1..6 sự kiện, thoi_diem trong 1 đơn không trùng nhau
--
-- Query dưới đây muốn gắn lên MỌI dòng sự kiện trạng thái đầu tiên và trạng thái
-- mới nhất của đơn. Dashboard hiện báo đơn "đang tao" dù đơn đã hoàn thành.
--
-- Yêu cầu: trang_thai_dau  = trang_thai của sự kiện sớm nhất của đơn
--          trang_thai_cuoi = trang_thai của sự kiện muộn nhất của đơn
--          (giữ nguyên số dòng — mỗi sự kiện 1 dòng, KHÔNG gộp về 1 dòng/đơn)
-- Cột kết quả: su_kien_id, trang_thai_dau, trang_thai_cuoi
-- Chấm:     python scripts/check.py B05

select
    su_kien_id,
    don_id,
    first_value(trang_thai) over (partition by don_id order by thoi_diem) as trang_thai_dau,
    last_value(trang_thai)  over (partition by don_id order by thoi_diem) as trang_thai_cuoi
from su_kien_don
