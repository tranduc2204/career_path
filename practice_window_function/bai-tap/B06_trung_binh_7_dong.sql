-- B06 · Trung bình trượt 7 DÒNG                             lý thuyết: 02 §4
-- Bảng: doanh_thu_ngay — CH02 nghỉ chủ nhật, CH03 và CH04 có ngày nghỉ (không có dòng)
--
-- Với mỗi (cua_hang, ngay):
--   tb_7_dong = trung bình doanh_thu của dòng hiện tại và tối đa 6 DÒNG liền trước (cùng cửa hàng)
--   so_dong   = số dòng thực sự nằm trong khung (dòng đầu chỉ có 1, 2, ...)
-- Cột kết quả: cua_hang, ngay, tb_7_dong, so_dong
--
-- Sau khi PASS: so sánh với B07 trên CH01 và CH03. Khi nào hai bài ra cùng kết quả?
-- Chấm:     python scripts/check.py B06

-- viết query bên dưới

