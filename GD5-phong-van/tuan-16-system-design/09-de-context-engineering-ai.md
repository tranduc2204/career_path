# 16.9 Đề 7 (Senior): Context engineering: cho AI trả lời câu hỏi số liệu

> Nền: GĐ3 tuần 8 (semantic layer), GĐ4 tuần 14 (AI context layer: semantic layer + dbt MCP server, đánh giá 50 câu hỏi) nếu đã làm.

## Đề

> *"Ban giám đốc muốn hỏi trợ lý AI kiểu 'doanh thu tuần trước ở miền Nam so với cùng kỳ thế nào?'. Một bản thử nghiệm cho LLM đọc schema rồi tự viết SQL: sai khoảng 40% và không ai biết câu nào sai. Thiết kế hệ thống để câu trả lời đáng tin."*

## Vì sao "LLM tự viết SQL trên schema" sai nhiều

| Nguyên nhân | Ví dụ |
|---|---|
| Không biết định nghĩa nghiệp vụ | "doanh thu" có trừ đơn huỷ? gồm phí ship? |
| Chọn sai bảng / join sai grain | join `fct_order_items` với `fct_orders` rồi `sum(total)` → fan-out |
| Không biết quy ước | "miền Nam" là những tỉnh nào? "tuần trước" bắt đầu thứ Hai hay Chủ nhật? |
| Bảng thừa / cũ | 3 bảng tên giống nhau, 2 cái đã bỏ |
| Không biết mình sai | trả lời tự tin, không trích nguồn |

**Context engineering** = thiết kế *thông tin, công cụ và ràng buộc* đưa cho model để nó làm đúng việc, thay vì chỉ viết prompt hay hơn.

## Kiến trúc

```
Người hỏi ──▶ AGENT (LLM)
                │  1. hiểu câu hỏi → chọn CÔNG CỤ, không viết SQL tự do
                ├──▶ tool: list_metrics / get_dimensions   ── semantic layer (MetricFlow / Cube)
                ├──▶ tool: query_metric(metrics, group_by, filters, time)  → SQL do semantic layer sinh
                ├──▶ tool: search_docs(glossary, định nghĩa)  ── tài liệu nghiệp vụ, description của dbt
                ├──▶ tool: get_lineage / freshness             ── dbt artifacts, Elementary (dữ liệu có mới không?)
                └──▶ (dự phòng) text-to-SQL có giới hạn: chỉ trên mart public, read-only, có giới hạn chi phí
                │  2. trả lời KÈM: metric đã dùng, bộ lọc, khoảng thời gian, độ tươi dữ liệu, link
                ▼
           ĐÁNH GIÁ & GIÁM SÁT: bộ câu hỏi chuẩn (golden set), log mọi câu hỏi + công cụ gọi + đáp án, phản hồi người dùng
```

Thành phần chính:

1. **Semantic layer làm "API số liệu":** agent chỉ chọn metric + dimension + filter. SQL đúng grain, đúng join, đúng định nghĩa do semantic layer sinh. Đây là thay đổi làm độ chính xác tăng nhiều nhất.
2. **Metadata giàu nghĩa:** `description`, `label`, từ đồng nghĩa ("doanh số" = `revenue`), ví dụ câu hỏi, đơn vị, metric nào certified (đề 5). Viết cho **máy đọc** cũng như người đọc.
3. **Glossary nghiệp vụ:** "miền Nam" = danh sách tỉnh, tuần bắt đầu thứ Hai, năm tài chính. Có thể là dimension (`region`), seed, hoặc tài liệu cho tool tìm kiếm.
4. **Công cụ qua MCP:** dbt MCP server cung cấp sẵn các tool đọc metadata dbt, lineage, truy vấn semantic layer. Agent dùng tool thay vì đoán.
5. **Ràng buộc an toàn:** quyền read-only theo **người hỏi** (row-level security, PII), giới hạn byte quét, không cho truy vấn bảng staging, timeout.
6. **Minh bạch:** mọi câu trả lời hiện metric, bộ lọc, thời gian và "dữ liệu cập nhật đến 06:30 hôm nay". Không chắc thì **hỏi lại**, không đoán.

## Đánh giá: phần nhiều ứng viên quên

| | Cách làm |
|---|---|
| Bộ câu hỏi chuẩn | 50–200 câu thật của người dùng, mỗi câu có **đáp án đúng** (số, hoặc truy vấn semantic layer chuẩn). Phân loại: đơn giản / có thời gian so sánh / có quy ước / mơ hồ / nên từ chối |
| Chỉ số | % đúng số, % chọn đúng metric, % hỏi lại khi mơ hồ, % từ chối đúng, độ trễ, chi phí/câu |
| So sánh | Có vs không có semantic layer; mô tả kém vs mô tả tốt (đo được giá trị của metadata) |
| Chạy khi nào | Mỗi lần đổi model, prompt, metadata, semantic layer (giống CI) |
| Sản xuất | Log mọi câu, mẫu ngẫu nhiên để người chấm, nút "sai" cho người dùng → câu sai vào bộ chuẩn |

## Đánh đổi

- **Semantic layer only:** đúng cao, nhưng chỉ trả lời được những gì đã mô hình hoá. Câu ngoài phạm vi phải từ chối hoặc chuyển cho analyst. Đây là tính năng, không phải lỗi.
- **Cho phép text-to-SQL dự phòng:** linh hoạt hơn nhưng độ đúng thấp. Phải gắn nhãn "chưa xác thực" và giới hạn trên mart public.
- **Chi phí và độ trễ:** nhiều lần gọi tool → chậm hơn. Cache metadata, saved query cho câu hỏi phổ biến.

## Câu hỏi đào sâu

1. **"Đo 'đúng' thế nào khi câu hỏi mơ hồ?"** → Bộ chuẩn có loại "mơ hồ" với đáp án kỳ vọng là **hỏi lại**. Chấm cả hành vi, không chỉ con số.
2. **"PII?"** → Agent truy vấn bằng danh tính người hỏi (không dùng service account quyền rộng), masking ở warehouse, không trả dữ liệu cấp khách hàng cho câu hỏi tổng hợp.
3. **"Dữ liệu hôm nay chưa về mà ai đó hỏi doanh thu hôm nay?"** → Tool freshness: trả lời kèm "dữ liệu tới hết ngày hôm qua" hoặc báo sự cố đang mở.
4. **"Ai sở hữu chất lượng của agent?"** → Đội dữ liệu sở hữu semantic layer + metadata + bộ đánh giá. Đội AI/nền tảng sở hữu agent. Bộ đánh giá là "hợp đồng" giữa hai bên.

## Câu trả lời 2 phút

> *"Em sẽ không để LLM viết SQL tự do. Agent hỏi qua semantic layer: chỉ chọn metric, dimension, bộ lọc. SQL đúng grain và đúng định nghĩa do semantic layer sinh. Phần việc chính của đội dữ liệu là context: mô tả metric viết cho cả máy đọc, từ đồng nghĩa, glossary như 'miền Nam' hay 'tuần', đánh dấu metric certified, và công cụ qua MCP để agent tra định nghĩa, lineage, độ tươi. Mọi câu trả lời hiện metric, bộ lọc và thời điểm dữ liệu. Không chắc thì hỏi lại. Quan trọng nhất là bộ đánh giá 100–200 câu hỏi thật có đáp án, chạy mỗi lần thay đổi, để biết độ đúng là 60% hay 95% thay vì đoán."*
