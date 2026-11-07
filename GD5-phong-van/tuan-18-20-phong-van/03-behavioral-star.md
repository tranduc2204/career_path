# 18.3 Câu hỏi hành vi: ngân hàng câu chuyện STAR

## STAR

| | Chiếm | Nội dung |
|---|---|---|
| **S**ituation | 15% | Bối cảnh ngắn: ở đâu, quy mô, vấn đề |
| **T**ask | 10% | Việc của **bạn** (không phải của đội) |
| **A**ction | 55% | Bạn làm gì, theo thứ tự, vì sao chọn cách đó (có đánh đổi) |
| **R**esult | 20% | Kết quả có số + **bài học** + bạn sẽ làm khác gì |

Dài 1,5–2,5 phút. Dùng "em" nhiều hơn "chúng em" ở phần Action.

## 8 câu chuyện cần chuẩn bị (mỗi câu dùng được cho nhiều câu hỏi)

| # | Câu chuyện | Nguồn (của bạn) | Trả lời được |
|---|---|---|---|
| 1 | Tối ưu / sửa một báo cáo chậm hoặc sai | BRAVO | "Vấn đề kỹ thuật khó nhất", "cải thiện hiệu năng" |
| 2 | Chuyển dữ liệu khi khách hàng đổi hệ thống | BRAVO (data migration) | "Làm việc dưới áp lực / deadline", "đảm bảo độ chính xác" |
| 3 | Sự cố dữ liệu CDC / pipeline | Estuary | "Kể một sự cố", "debug" |
| 4 | Một lỗi do chính bạn gây ra | BRAVO / Estuary / lab (bạn đã thật sự sai ở đâu?) | "Thất bại", "sai lầm" |
| 5 | Tự học và áp dụng một thứ mới nhanh | 5 tháng roadmap: Data Vault / semantic layer | "Học nhanh", "chủ động" |
| 6 | Không đồng ý với người khác / khách hàng | BRAVO (yêu cầu báo cáo của khách) | "Xung đột", "thuyết phục" |
| 7 | Giải thích kỹ thuật cho người không kỹ thuật | Kế toán khách hàng BRAVO / blog | "Giao tiếp" |
| 8 | Một quyết định có đánh đổi | ADR: Data Vault vs Kimball, Dagster vs Airflow | "Ra quyết định", "tư duy kiến trúc" |

## Mẫu điền (câu chuyện 2)

> **S:** Ở BRAVO, khách hàng [ngành] nâng cấp ERP từ [phiên bản] lên [phiên bản], cần chuyển [N năm / N bảng / N triệu dòng] dữ liệu [kế toán/kho] trong [thời gian].
> **T:** Em phụ trách [phần cụ thể: viết script chuyển + đối soát số dư].
> **A:** Em [1] lập danh sách bảng và quy tắc ánh xạ, [2] viết script chuyển theo kỳ để chạy lại được từng kỳ, [3] viết truy vấn đối soát tổng số dư theo tài khoản kế toán và theo kỳ giữa hai hệ thống, [4] chạy thử trên bản sao, phát hiện [vấn đề cụ thể], [5] …
> **R:** Chuyển xong trong [thời gian], đối soát lệch [0 / N trường hợp đã giải thích], khách hàng nghiệm thu [ngày]. Bài học: đối soát phải viết **trước** khi chuyển. Đó cũng là thứ em làm lại trong take-home ngân hàng: bảng đối soát với sổ cái.

## Câu hỏi hành vi hay gặp

1. Giới thiệu bản thân (2 phút: hiện tại → quá khứ liên quan → vì sao vị trí này).
2. Vì sao chuyển sang analytics engineering?
3. Kể một dự án bạn tự hào nhất.
4. Kể một lần bạn sai và cách bạn xử lý.
5. Kể một lần bất đồng với đồng nghiệp / quản lý / khách hàng.
6. Bạn ưu tiên khi có nhiều yêu cầu cùng lúc thế nào?
7. Kể một lần bạn phải học thứ mới rất nhanh.
8. Bạn đảm bảo con số mình đưa ra là đúng bằng cách nào?
9. Kể một lần bạn đơn giản hoá thứ phức tạp cho người khác hiểu.
10. Điểm yếu của bạn? (nêu một điểm thật + việc đang làm để cải thiện: vd "kinh nghiệm production với dbt còn ngắn → em bù bằng lab mô phỏng sự cố và project có CI/CD thật")
11. Vì sao công ty chúng tôi?
12. 2–3 năm tới bạn muốn ở đâu?
13. Bạn có câu hỏi gì cho chúng tôi?

## Câu hỏi bạn nên hỏi lại (chọn 2–3)

- Đội dữ liệu hiện có bao nhiêu người, chia theo domain hay theo tầng?
- dbt project hiện có bao nhiêu model, CI/CD thế nào, ai duyệt PR?
- Thước đo thành công của vị trí này trong 6 tháng đầu là gì?
- Sự cố dữ liệu gần nhất là gì và đội xử lý thế nào? (câu này cho bạn biết rất nhiều về độ trưởng thành)
- Ai là người dùng chính của đội dữ liệu, và họ hài lòng nhất / ít nhất về điều gì?

## Luyện

Mỗi ngày tuần 18–20: kể to 1 câu chuyện, ghi âm, bấm giờ. Mỗi câu chuyện kể ≥ 3 lần trước buổi phỏng vấn đầu tiên. Viết ra gạch đầu dòng, **không** học thuộc lòng nguyên văn.
