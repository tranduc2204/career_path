-- B15 · Chia phiên (sessionization)                         lý thuyết: 02 §3, 03 §4
-- Bảng: giao_dich
--
-- Thứ tự giao dịch của khách: (thoi_diem, giao_dich_id).
-- Giao dịch mở PHIÊN MỚI nếu là giao dịch đầu tiên của khách, hoặc cách giao dịch liền
-- trước HƠN 30 phút (đúng 30 phút vẫn cùng phiên).
--   phien_so = số thứ tự phiên của khách, bắt đầu từ 1
-- Cột kết quả: giao_dich_id, phien_so
-- Gợi ý: LAG để gắn cờ "phiên mới" (0/1) → lũy kế cờ.
-- Chấm:     python scripts/check.py B15

-- viết query bên dưới

