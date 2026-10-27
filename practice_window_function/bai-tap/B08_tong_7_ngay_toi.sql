-- B08 · Doanh thu 7 ngày TỚI (nhìn về tương lai)            lý thuyết: 02 §2, §6 (khung rỗng)
-- Bảng: doanh_thu_ngay
--
-- Dùng làm "nhãn" cho mô hình dự báo: với mỗi (cua_hang, ngay)
--   tong_7_ngay_toi = tổng doanh_thu các ngày từ (ngay + 1) tới (ngay + 7), KHÔNG gồm hôm nay.
--                     Nếu khoảng đó không có dòng nào → 0 (không phải NULL).
-- Cột kết quả: cua_hang, ngay, tong_7_ngay_toi
-- Chấm:     python scripts/check.py B08

-- viết query bên dưới

