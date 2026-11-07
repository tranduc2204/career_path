# 16.6 Đề 4: Chuyển hệ thống báo cáo stored procedure sang dbt

> Đề này **gắn với kinh nghiệm thật của bạn ở BRAVO** (stored procedure, báo cáo BI, data migration). Người phỏng vấn sẽ rất hay hỏi kiểu này khi đọc CV. Hãy chuẩn bị cả bản "thiết kế" lẫn bản "câu chuyện" (16.6 cuối file và tuần 18 [STAR](../tuan-18-20-phong-van/03-behavioral-star.md)).

## Đề

> *"Công ty có khoảng 150 stored procedure trên SQL Server sinh báo cáo cho kế toán, kho và bán hàng. Chạy bằng SQL Agent lúc 2 giờ sáng. Không có test, không có tài liệu, người viết phần lớn đã nghỉ. Chúng tôi muốn chuyển sang dbt trên một cloud warehouse. Bạn lên kế hoạch và thiết kế thế nào?"*

## Bước 1: Làm rõ

| Câu hỏi | Giả định | Vì sao |
|---|---|---|
| Vì sao chuyển? (đau ở đâu) | Chạy 4 tiếng, hay lỗi, không ai dám sửa, muốn thêm nguồn mới | Mục tiêu quyết định thứ tự |
| Bao nhiêu báo cáo thật sự đang được dùng? | Không rõ | → bước kiểm kê là bắt buộc |
| Warehouse đích? Dữ liệu nguồn chuyển sang bằng gì? | Snowflake; ingest bằng Fivetran/Airbyte từ SQL Server (CDC) | Tầng raw có sẵn |
| Báo cáo cũ có được tắt dần không? Ai ký nghiệm thu? | Có, kế toán trưởng ký từng báo cáo | → tiêu chí cắt chuyển |
| Thời hạn? Đội? | 6 tháng, 2 AE + 1 DE | → phải ưu tiên |
| Procedure có ghi ngược vào hệ thống nguồn (writeback) không? | Vài cái cập nhật bảng trạng thái của ERP | → **phạm vi ngoài dbt** |

## Bước 2: Ước lượng và kiểm kê

Kiểm kê trước khi viết dòng dbt nào:

| Việc | Cách | Kết quả mong đợi |
|---|---|---|
| Procedure nào còn được gọi | Log SQL Agent, `sys.dm_exec_procedure_stats`, lịch sử chạy 90 ngày | Thường chỉ 40–60% còn dùng |
| Báo cáo nào còn người xem | Log của công cụ BI, hỏi người dùng | Danh sách báo cáo + chủ |
| Phụ thuộc | Đọc mã: procedure gọi procedure, bảng tạm, bảng trung gian ghi đè | Đồ thị phụ thuộc |
| Độ phức tạp | Đếm dòng, cursor, dynamic SQL, `UPDATE` từng bước | Xếp hạng khó/dễ |

Ví dụ kết quả: 150 procedure → 70 còn chạy → phục vụ 35 báo cáo còn người xem → 12 báo cáo chiếm 80% lượt xem. **12 báo cáo đó là phạm vi đợt 1.**

## Bước 3: Kiến trúc đích

```
SQL Server (ERP) ──CDC──▶ raw (bất biến) ──▶ staging ──▶ intermediate ──▶ marts (Kimball) ──▶ BI
                                                 ▲              ▲
                                       thay cho "bảng tạm"   thay cho các bước UPDATE nối tiếp
                                       trong procedure        (mỗi bước = 1 model có tên)
song song trong giai đoạn chuyển: báo cáo cũ (SQL Server) ◀── đối chiếu tự động ──▶ báo cáo mới (dbt)
```

## Bước 4: Đi sâu

### 4.1 Dịch procedure sang dbt: không dịch từng dòng

Procedure kiểu cũ thường là: tạo bảng tạm → nhiều `UPDATE` nối tiếp → `INSERT` vào bảng báo cáo → xoá bảng tạm. Cách chuyển:

| Trong procedure | Trong dbt |
|---|---|
| `SELECT ... INTO #tmp` | model `int_*` (ephemeral hoặc view) có tên nói lên ý nghĩa |
| Chuỗi `UPDATE #tmp SET ... WHERE ...` | các CTE / model nối tiếp, mỗi bước **thêm cột**, không ghi đè |
| Cursor duyệt từng dòng | window function, `qualify`, tập hợp |
| Dynamic SQL theo tham số | Jinja (`var`, vòng lặp, macro), hoặc semantic layer cho tham số báo cáo |
| `DELETE` + `INSERT` theo kỳ | incremental `delete+insert` theo kỳ, hoặc `table` nếu nhỏ |
| Logic nghiệp vụ lặp ở 10 procedure (vd quy đổi đơn vị, tính giá vốn) | **một** model/macro dùng chung |
| Hard-code mã chi nhánh, mã tài khoản kế toán | seed / bảng tham chiếu có chủ sở hữu |

Quy trình cho mỗi báo cáo:
1. **Đặc tả ngược:** chạy procedure trên một kỳ đã khoá, lưu kết quả làm "golden output".
2. Viết lại thành DAG dbt theo chuẩn tầng.
3. **Đối chiếu tự động** với golden output (`audit_helper.compare_queries` hoặc SQL EXCEPT theo khoá + so tổng): 0 dòng khác → xong; có khác → hoặc dbt sai, hoặc **procedure cũ sai** (rất hay gặp!) → ghi lại, hỏi chủ báo cáo quyết định.
4. Chạy song song ≥ 2 kỳ khoá sổ, chủ báo cáo ký, rồi tắt procedure.

### 4.2 Khi procedure cũ sai

Đây là phần "chính trị" của đề. Ví dụ: procedure tính tồn kho bỏ sót hàng trả về từ năm 2021. Số mới "đúng" nhưng **khác** số kế toán đã báo cáo 3 năm. Cách xử lý:

- Không tự quyết. Trình bày chênh lệch kèm bằng chứng (dòng cụ thể) cho chủ báo cáo.
- Đề xuất: (a) số mới từ kỳ X trở đi + ghi chú, (b) giữ cách tính cũ (sai) có tên rõ ràng nếu bắt buộc vì lý do kế toán, (c) điều chỉnh lịch sử.
- Ghi quyết định vào ADR/README của model.

### 4.3 Thứ tự chuyển

- Theo **domain**, bắt đầu từ báo cáo có giá trị cao + phụ thuộc ít (thường là bán hàng). Kho và kế toán (giá vốn, công nợ) phức tạp hơn, làm sau khi đã có `dim_product`, `dim_customer` dùng chung.
- Mỗi đợt kết thúc bằng **tắt** được thứ gì đó. Chuyển xong mà không tắt cái cũ thì chỉ là thêm một hệ thống phải bảo trì.

### 4.4 Những thứ không thuộc dbt

- Writeback vào ERP → giữ ở hệ thống nguồn hoặc chuyển sang công cụ reverse ETL / job ứng dụng. dbt chỉ biến đổi trong warehouse.
- Báo cáo cần tham số do người dùng nhập (từ ngày, đến ngày, chi nhánh) → tham số đi vào BI / semantic layer, không vào dbt.
- Gửi email file Excel → BI có lịch gửi, hoặc job riêng đọc mart.

## Bước 5: Vận hành và rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Số mới khác số cũ, mất niềm tin | Đối chiếu tự động mỗi ngày trong thời gian song song, dashboard "tiến độ khớp số" cho người dùng xem |
| Logic ngầm không ai biết | Golden output trên nhiều kỳ (cuối tháng, cuối năm, kỳ có điều chỉnh) |
| Người dùng không chịu đổi | Mỗi báo cáo mới phải **nhanh hơn / thêm được gì** (drill-down, cập nhật sớm hơn) |
| Kéo dài vô hạn | Phạm vi theo đợt, mỗi đợt có ngày tắt hệ thống cũ |

Đo thành công: số procedure đã tắt, thời gian chạy đêm (4 giờ → 30 phút), số lỗi chạy đêm/tháng, thời gian trả lời yêu cầu báo cáo mới.

## Câu hỏi đào sâu + ý trả lời

1. **"Procedure 3.000 dòng không ai hiểu?"** → Chạy và chụp kết quả trung gian (bảng tạm sau mỗi bước) trên một kỳ, viết lại từng bước thành model và so từng bước. Chia để trị.
2. **"T-SQL và Snowflake SQL khác nhau?"** → Danh sách chuyển đổi (ISNULL → COALESCE, TOP → LIMIT, datetime, collation không phân biệt hoa thường của SQL Server, phép chia số nguyên), sqlglot để dịch nháp, đối chiếu kết quả để bắt khác biệt ngầm (collation và làm tròn là thủ phạm hay gặp).
3. **"Có nên giữ SQL Server làm warehouse và chạy dbt trên đó?"** → dbt-sqlserver tồn tại. Nếu mục tiêu chính là khả năng bảo trì chứ không phải hiệu năng, chuyển sang dbt **trước**, đổi warehouse **sau** giảm rủi ro (một thay đổi mỗi lần). Đây là câu trả lời Senior.

## Kể bằng kinh nghiệm của bạn

Khung câu chuyện (điền số thật của bạn ở BRAVO):

> *"Ở BRAVO em làm với nhiều stored procedure báo cáo cho khách hàng ERP. Vấn đề là [chạy chậm / sai số / khó sửa]. Em đã [tối ưu procedure X từ A phút xuống B phút / viết lại logic Y / chuyển dữ liệu khi khách hàng đổi phiên bản]. Bài học: không có test và đối chiếu thì sửa gì cũng sợ. Đó là lý do em học dbt: mỗi bước có tên, có test, có lineage. Trong project adventure_works, em [dựng lại một báo cáo kiểu đó bằng dbt, có test đối soát]."*

Đừng nói quá. Người phỏng vấn sẽ hỏi chi tiết: bao nhiêu procedure, procedure dài nhất bao nhiêu dòng, bạn đã làm gì cụ thể.
