-- B12 · Tổng 3 MỐC thời điểm gần nhất (dùng GROUPS)          lý thuyết: 02 §3, §4
-- Bảng: giao_dich — có giao dịch trùng thoi_diem
--
-- "Mốc" = một giá trị thoi_diem khác nhau của khách. Với mỗi giao dịch:
--   tong_3_moc = tổng so_tien của khách trong mốc hiện tại + 2 mốc liền trước
--                (mọi giao dịch trong 3 mốc đó, dù 1 mốc có nhiều giao dịch)
-- Cột kết quả: giao_dich_id, tong_3_moc
-- Chấm:     python scripts/check.py B12

-- viết query bên dưới

