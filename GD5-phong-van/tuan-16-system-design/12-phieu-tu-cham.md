# 16.12 Phiếu tự chấm và quy trình mock interview

## Quy trình một buổi luyện (75 phút)

1. **Rút đề** (`python tools/drill.py`, hoặc chọn từ đề 1–8, D1–D14). Không đọc lời giải.
2. **Bật ghi âm / quay màn hình.** Vẽ trên giấy A3 hoặc Excalidraw.
3. **Làm 45 phút** theo đồng hồ của `drill.py` (nó nhắc chuyển bước), nói thành tiếng như có người nghe.
4. **Nghỉ 5 phút**, rồi nghe lại ghi âm với phiếu dưới đây (15 phút).
5. **So với lời giải mẫu** (nếu có) hoặc [16.2 thư viện mẫu](02-thu-vien-mau-thiet-ke.md): ghi 3 điều thiếu (10 phút).
6. Ghi vào nhật ký luyện tập (cuối file). Làm lại đề đó sau 3 ngày.

Với mock có người thật: người kia đọc đề, trả lời câu hỏi làm rõ theo bảng giả định của đề (hoặc tự bịa hợp lý), cắt ngang 2 lần bằng câu hỏi đào sâu, chấm bằng phiếu.

## Phiếu chấm (0–3 mỗi dòng)

0 = không có · 1 = có nhưng yếu · 2 = đạt mức Mid · 3 = mức Senior

| # | Tiêu chí | Câu tự hỏi khi nghe lại | Điểm |
|---|---|---|---|
| 1 | Làm rõ yêu cầu | Có hỏi đủ người dùng / nguồn / độ tươi / ràng buộc / đội? Có chốt giả định thành lời và ghi lên bảng? | |
| 2 | Yêu cầu đo được | Có 3–5 yêu cầu chức năng và SLA/độ đúng cụ thể? | |
| 3 | Ước lượng | Có con số? Con số có dẫn tới quyết định (incremental, partition, chi phí)? | |
| 4 | Kiến trúc | Sơ đồ rõ, mũi tên có nhãn, mỗi tầng có lý do một câu? | |
| 5 | Grain và mô hình | Nói được grain + khoá của 2–3 bảng chính? SCD/semi-additive đúng chỗ? | |
| 6 | Thời gian và dữ liệu trễ | Có xử lý late data, sửa ngược, idempotent, backfill? | |
| 7 | Đánh đổi | Ít nhất 2 chỗ nêu 2 phương án + tiêu chí + lựa chọn? | |
| 8 | Chất lượng | Test ở đâu, freshness, đối soát, severity, ai nhận cảnh báo? | |
| 9 | Triển khai | Môi trường, CI/CD, rollback? | |
| 10 | Bảo mật / tuân thủ | PII, quyền, audit (nếu đề liên quan)? | |
| 11 | Chi phí | Có nhắc và có cách kiểm soát? | |
| 12 | Tổ chức | Owner, đội, lộ trình v1/v2/v3? | |
| 13 | Giao tiếp | Có cấu trúc, kiểm tra lại với người nghe, không im lặng lâu, đúng giờ? | |
| 14 | Kinh nghiệm thật | Có dẫn chứng từ lab / adventure_works / thelook / BRAVO / Estuary? | |

**Tổng /42.** Mục tiêu: ≥ 28 (trung bình 2) cho Mid; dòng 1, 5, 7 phải ≥ 2.

## Câu hỏi đào sâu "đa năng"

Người luyện cùng (hoặc bạn tự hỏi mình) dùng các câu này để cắt ngang:

- "Nếu dữ liệu tăng 10 lần thì chỗ nào vỡ đầu tiên?"
- "Bỏ tầng X đi được không? Điều gì xảy ra?"
- "Dữ liệu đến trễ 5 ngày thì sao?"
- "Ai được xem bảng này?"
- "Nó hỏng lúc 3 giờ sáng. Ai biết, làm gì?"
- "Em chỉ có 1 người và 2 tháng. Em cắt gì?"
- "Tốn bao nhiêu tiền một tháng?"
- "Làm sao biết số này đúng?"

## Nhật ký luyện tập

| Ngày | Đề | Thời gian | Điểm /42 | 3 điểm thiếu | Làm lại ngày |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
