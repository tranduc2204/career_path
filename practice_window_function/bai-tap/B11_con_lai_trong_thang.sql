-- B11 · Doanh thu còn lại trong tháng                       lý thuyết: 02 §2, §6
-- Bảng: doanh_thu_ngay
--
-- Với mỗi (cua_hang, ngay):
--   con_lai_trong_thang = tổng doanh_thu của cửa hàng ở các ngày SAU hôm nay, CÙNG tháng.
--                         Ngày cuối tháng (hoặc không còn ngày nào) → 0.
-- Cột kết quả: cua_hang, ngay, con_lai_trong_thang
-- Kiểm tra nhanh: luy_ke_trong_thang + con_lai_trong_thang = tổng tháng (với mọi dòng).
-- Chấm:     python scripts/check.py B11

-- viết query bên dưới

