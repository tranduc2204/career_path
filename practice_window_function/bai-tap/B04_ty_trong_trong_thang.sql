-- B04 · Tỉ trọng trong tháng                                lý thuyết: 02 §2 (không ORDER BY), 01 §5 (WINDOW)
-- Bảng: doanh_thu_ngay
--
-- Với mỗi (cua_hang, ngay):
--   ty_trong_thang  = doanh_thu / tổng doanh_thu cả tháng của cửa hàng đó        (0..1)
--   ty_trong_luy_ke = tổng doanh_thu từ đầu tháng tới hết hôm nay / tổng cả tháng (tăng dần tới 1)
-- Tháng = date_trunc('month', ngay). Không cần làm tròn.
--
-- Cột kết quả: cua_hang, ngay, ty_trong_thang, ty_trong_luy_ke
-- Thử thêm: dùng mệnh đề WINDOW để đặt tên 2 cửa sổ.
-- Chấm:     python scripts/check.py B04

-- viết query bên dưới

