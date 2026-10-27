-- B10 · Điền giá bị thiếu (forward fill + back fill)        lý thuyết: 02 §5, 03 §2
-- Bảng: gia_niem_yet(san_pham_id, ngay, gia) — mỗi sản phẩm 21 ngày, ngày không đổi giá thì gia = NULL
--
-- gia_da_dien =
--   1. gia khác NULL gần nhất tính tới hôm nay (gồm hôm nay)                 -- forward fill
--   2. nếu từ đầu tới hôm nay chưa có giá nào → gia khác NULL đầu tiên phía sau -- back fill
--   3. sản phẩm không có giá nào cả → NULL
-- Cột kết quả: san_pham_id, ngay, gia_da_dien
-- Bonus (không chấm): viết lại phần forward fill KHÔNG dùng IGNORE NULLS (mẹo COUNT tạo nhóm).
-- Chấm:     python scripts/check.py B10

-- viết query bên dưới

