-- B09 · Ngày lập kỷ lục                                     lý thuyết: 02 §6 (loại dòng hiện tại)
-- Bảng: doanh_thu_ngay
--
-- Với mỗi (cua_hang, ngay):
--   max_truoc_do = doanh_thu cao nhất của cửa hàng ở các ngày TRƯỚC hôm nay (không tính hôm nay).
--                  Ngày đầu tiên → NULL.
--   la_ky_luc    = TRUE nếu hôm nay vượt HẲN max_truoc_do (bằng thì không tính), hoặc là ngày đầu tiên.
-- Cột kết quả: cua_hang, ngay, max_truoc_do, la_ky_luc (kiểu BOOLEAN)
-- Chấm:     python scripts/check.py B09

-- viết query bên dưới

