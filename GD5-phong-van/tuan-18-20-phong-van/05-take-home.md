# 18.5 Làm bài take-home

> Luyện bằng bài mẫu có chấm tự động: [bai-tap-take-home](../../bai-tap-take-home/README.md) ("Ngân hàng số Sen", 6 giờ).

## Trước khi bắt đầu

- **Hỏi lại** những gì mơ hồ qua email (1 lần, gom câu hỏi). Không ai trả lời thì ghi giả định vào README. Cả hai đều là điểm cộng.
- Hỏi: giới hạn thời gian thật, có được dùng package/AI không, nộp dạng gì, ai sẽ đọc.
- Bấm giờ. Làm quá giới hạn nhiều thì nói thật trong README ("em dành thêm 2 giờ cho phần X").

## Phân bổ thời gian (bài 4–6 giờ)

| % thời gian | Việc |
|---|---|
| 15% | Khảo sát dữ liệu: grain, khoá, NULL, trùng, ngày giờ, giá trị lạ. **Ghi giả định ngay** |
| 50% | Model theo tầng, đúng yêu cầu trước, đẹp sau |
| 15% | Test (khoá, quan hệ, luật nghiệp vụ, đối soát) + description |
| 15% | README |
| 5% | Chạy lại từ đầu trên môi trường sạch, đọc lại như người chấm |

## README của bài nộp: khung

```markdown
# [Tên bài] — lời giải
## Chạy thế nào (≤ 3 lệnh)
## Kết quả (bảng nào, grain gì, trả lời yêu cầu nào)
## Giả định (đánh số, mỗi cái 1 dòng)
## Quyết định thiết kế (vì sao chọn X thay vì Y)
## Phát hiện về dữ liệu (điều bất thường, số lệch và nguyên nhân bạn nghĩ tới)
## Chất lượng (test gì, vì sao)
## Nếu có thêm thời gian / ở production (incremental, CI/CD, chi phí, PII...)
```

Phần "Phát hiện" thường là phần người chấm nhớ nhất: ví dụ dòng lệch sổ cái trong bài Sen Bank.

## Đừng

- Nộp một file SQL 400 dòng.
- Bỏ qua yêu cầu khó mà không giải thích.
- Dùng AI sinh code mà không hiểu: vòng đọc lại bài sẽ hỏi từng dòng. (Nếu được phép dùng, ghi rõ đã dùng cho việc gì.)
- Tối ưu sớm (incremental phức tạp cho 10.000 dòng). Viết `table`, rồi giải thích sẽ làm incremental ra sao ở production.

## Vòng đọc lại bài (45 phút)

Chuẩn bị:

- Trình bày 5 phút: kiến trúc, 2 quyết định, 1 phát hiện.
- Tự liệt kê 3 điểm yếu của bài trước khi họ chỉ ra. Chủ động nói "ở production em sẽ đổi chỗ này".
- Sẵn sàng sửa code trực tiếp (thêm cột, đổi grain, thêm test) trong 10 phút.
- Các câu hỏi mẫu: phần "Vòng đọc lại bài" của [bài take-home](../../bai-tap-take-home/README.md).
