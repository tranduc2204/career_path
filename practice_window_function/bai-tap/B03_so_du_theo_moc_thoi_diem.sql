-- B03 · Số dư theo MỐC thời điểm                            lý thuyết: 02 §3
-- Bảng: giao_dich (như B02)
--
-- Ngược với B02: team đối soát muốn "số dư của khách tại thời điểm T" — tức là đã cộng
-- TẤT CẢ giao dịch có thoi_diem <= T, kể cả các giao dịch khác cùng thời điểm với dòng này.
-- (Giao dịch cùng thoi_diem phải ra cùng một so_du.)
--
-- Cột kết quả: giao_dich_id, so_du
-- Câu hỏi để tự trả lời: tại sao ở bài này frame mặc định lại "đúng"? Vẫn nên viết tường minh.
-- Chấm:     python scripts/check.py B03

-- viết query bên dưới

