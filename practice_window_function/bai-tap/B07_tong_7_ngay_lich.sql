-- B07 · Tổng 7 NGÀY LỊCH (rolling 7 days)                   lý thuyết: 02 §4, 03 §3
-- Bảng: doanh_thu_ngay — có ngày nghỉ (không có dòng)
--
-- Với mỗi (cua_hang, ngay):
--   tong_7_ngay    = tổng doanh_thu của cửa hàng trong các ngày từ (ngay - 6) tới ngay
--   so_ngay_co_ban = số dòng trong khoảng đó (≤ 7)
-- Cột kết quả: cua_hang, ngay, tong_7_ngay, so_ngay_co_ban
--
-- Đây là bẫy kinh điển trong dashboard "doanh thu 7 ngày gần nhất".
-- Bonus (không chấm): viết thêm cách 2 dùng date spine + ROWS — cách duy nhất khi warehouse
-- không hỗ trợ RANGE với INTERVAL.
-- Chấm:     python scripts/check.py B07

-- viết query bên dưới

