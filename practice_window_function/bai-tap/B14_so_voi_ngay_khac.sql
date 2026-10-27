-- B14 · So với các ngày KHÁC trong tháng (EXCLUDE)          lý thuyết: 02 §6
-- Bảng: doanh_thu_ngay — CH04 chỉ có đúng 1 ngày trong tháng 9
--
-- Với mỗi (cua_hang, ngay):
--   chenh_lech = doanh_thu - trung bình doanh_thu của các ngày KHÁC cùng cửa hàng, cùng tháng.
--                Không có ngày nào khác → NULL.
-- Cột kết quả: cua_hang, ngay, chenh_lech
-- Làm 2 cách: (1) EXCLUDE CURRENT ROW, (2) portable không dùng EXCLUDE. Nộp cách nào cũng được.
-- Chấm:     python scripts/check.py B14

-- viết query bên dưới

