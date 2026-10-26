# 7.1 Tư duy performance và chi phí

> Mục tiêu tuần 7: một **performance playbook** cho Snowflake và BigQuery, viết từ số đo của chính bạn. File này là phần "cách nghĩ" dùng chung cho cả hai.

## Hai mô hình tính tiền khác nhau → hai cách tối ưu khác nhau

| | Snowflake | BigQuery on-demand |
|---|---|---|
| Trả tiền cho | **Thời gian warehouse chạy** × kích cỡ warehouse (credit) | **Số byte dữ liệu quét** |
| Đơn vị | XS = 1 credit/giờ, mỗi cấp gấp đôi. Tính theo giây, **tối thiểu 60 giây** mỗi lần warehouse bật | $ / TiB quét (US multi-region: 6,25 USD/TiB, **1 TiB đầu mỗi tháng miễn phí**). Tối thiểu 10 MB / bảng được tham chiếu, làm tròn lên MB |
| Query chạy 2 phút trên warehouse đang mở | Tốn 2 phút credit (dù chỉ quét 1 MB) | Tốn theo byte quét (dù chạy 2 phút) |
| Đòn bẩy chính | Giảm **thời gian** chạy, chọn **đúng cỡ** warehouse, **tắt** warehouse khi rảnh | Giảm **byte quét**: chọn ít cột, partition, cluster |
| `select *` | Chậm hơn (đọc nhiều cột hơn) | **Đắt hơn trực tiếp**: trả tiền cho mọi cột |
| Kết quả cache | Result cache 24h: miễn phí | Cache hit: miễn phí |

BigQuery còn mô hình **capacity** (editions, trả theo slot-giờ) giống Snowflake hơn: trả theo năng lực tính toán thay vì byte. Công ty lớn hay dùng. Lab tuần 5, 7 dùng on-demand.

Bảng giá đổi theo thời gian và khu vực: luôn kiểm tra trang giá chính thức trước khi ghi số vào playbook.

## Phương pháp: đo → giả thuyết → đổi 1 thứ → đo lại

```
1. ĐO        Lấy số thật: thời gian, byte quét, credit. Từ query history, không đoán.
2. XẾP HẠNG  80/20: thường 20% model/query gây 80% chi phí. Làm từ cái đắt nhất.
3. GIẢ THUYẾT "Model này quét toàn bảng vì filter không prune được partition"
4. ĐỔI 1 THỨ Chỉ đổi đúng 1 biến (thêm partition, đổi cỡ warehouse...). Đổi nhiều thứ cùng lúc thì không biết cái nào có tác dụng
5. ĐO LẠI     Cùng query, cùng dữ liệu. Tắt cache khi đo (Snowflake: USE_CACHED_RESULT = FALSE)
6. GHI LẠI    Vào playbook: trước / sau / kết luận. Kết quả âm (không cải thiện) cũng ghi
```

## Đo ở đâu

| Nguồn | Có gì |
|---|---|
| `target/run_results.json` của dbt | `execution_time` từng node, trạng thái, `adapter_response` (BigQuery có `bytes_processed`, `bytes_billed`; Snowflake có `query_id`) |
| Snowflake `QUERY_HISTORY` | Thời gian, warehouse, byte quét, partition quét/tổng, spill, `query_tag` (7.3) |
| Snowflake `QUERY_ATTRIBUTION_HISTORY` | Credit **gán cho từng query** (không tính thời gian warehouse rảnh). Trễ tới 8 giờ |
| BigQuery `INFORMATION_SCHEMA.JOBS` | Byte quét, byte tính tiền, slot-ms, cache, `labels` (7.5) |
| Query Profile (Snowflake) / Execution details (BigQuery) | Kế hoạch thực thi của 1 query: chậm ở bước nào |

Gắn nhãn để biết query nào của model nào:
- Snowflake: config `query_tag` (dbt đặt `ALTER SESSION SET QUERY_TAG`).
- BigQuery: `labels` của model + `query-comment` với `job-label: true` (7.5).

## Đòn bẩy ở tầng dbt (trước cả khi đụng SQL)

| Đòn bẩy | Tác dụng |
|---|---|
| **Materialization** | View chạy lại mọi lần BI đọc; table chạy lại mọi lần build; incremental chỉ xử lý phần mới (GĐ1) |
| **Chọn đúng phần cần build** | Slim CI `state:modified+` + `--defer` (GĐ1, 3.2). `dbt clone` để có bảng incremental trong CI mà không full refresh |
| **Lịch chạy** | Model đổi theo ngày không cần chạy mỗi giờ. Tách job theo tần suất (tag `hourly`, `daily`) |
| **Test** | Test cũng là query! `unique` trên bảng 2 tỷ dòng = quét cả bảng. Dùng `where` (config của test) để chỉ test dữ liệu gần đây, hoặc chạy test nặng theo lịch riêng |
| **Ephemeral / CTE lặp** | Model ephemeral được nhúng vào mọi nơi dùng nó → có thể bị tính nhiều lần |
| **Warehouse theo model** (Snowflake) | Model nặng dùng warehouse lớn, còn lại dùng XS (`snowflake_warehouse`) |

## Phản mẫu SQL hay gặp

| Phản mẫu | Vì sao tốn | Sửa |
|---|---|---|
| `select *` ở tầng mart | Đọc mọi cột (BigQuery: trả tiền mọi cột) | Liệt kê cột cần |
| Hàm bọc cột lọc: `where date(created_at) = ...`, `cast(col as ...)` | Có thể làm mất pruning (tuỳ nền tảng, tuỳ hàm) | Lọc trực tiếp trên cột: `created_at >= ... and created_at < ...` |
| Join bùng nổ (exploding join) | Khoá join không duy nhất → số dòng nhân lên | Kiểm tra grain trước khi join (test unique) |
| `distinct` để "chữa" trùng | Tốn sort/hash, che giấu lỗi join | Sửa join |
| `union` thay vì `union all` | Phải loại trùng | `union all` khi không cần loại trùng |
| `order by` trong model | Sort toàn bảng vô ích (bảng không giữ thứ tự cho người đọc) | Bỏ, trừ khi có lý do (cluster) |
| Lọc sau khi join / sau window function | Xử lý nhiều dữ liệu hơn cần | Lọc sớm nhất có thể |
| CTE được tham chiếu nhiều lần | BigQuery có thể tính lại CTE mỗi lần tham chiếu | Tách thành model `table` nếu nặng |
| Window function trên partition khổng lồ | Dồn một lượng lớn dữ liệu về một chỗ, dễ spill | Thu hẹp partition, lọc trước |

## Rào chắn chi phí (guardrails)

Tối ưu là việc làm dần. Rào chắn phải có **ngay từ ngày đầu**:

| Nền tảng | Rào chắn |
|---|---|
| Snowflake | Resource monitor (dừng warehouse khi vượt quota), `AUTO_SUSPEND` ngắn, `STATEMENT_TIMEOUT_IN_SECONDS` |
| BigQuery | `maximum_bytes_billed` trong `profiles.yml` (query vượt ngưỡng bị chặn), quota theo ngày của project, budget alert của Cloud Billing |
| dbt | `require_partition_filter` cho bảng lớn, review PR có model full scan |

## Lỗi hay gặp

- Tối ưu theo cảm giác, không đo trước.
- Đổi nhiều thứ cùng lúc rồi không biết cái nào có tác dụng.
- Đo khi cache đang bật → kết quả đẹp giả.
- Chỉ tối ưu model, quên rằng test và dashboard cũng chạy query.
- Không có rào chắn → một query lỗi đốt cả tháng ngân sách.
- Áp kinh nghiệm Snowflake sang BigQuery (hoặc ngược lại) mà không nghĩ tới mô hình tính tiền.

## Câu hỏi tự kiểm tra

1. Snowflake và BigQuery on-demand tính tiền theo cái gì? Hệ quả cho việc tối ưu?
2. Vì sao `select *` đắt trực tiếp trên BigQuery nhưng chỉ chậm hơn trên Snowflake?
3. Kể 6 bước của phương pháp tối ưu. Vì sao chỉ đổi 1 thứ mỗi lần?
4. Ở tầng dbt có những đòn bẩy nào trước khi phải sửa SQL?
5. Kể 5 phản mẫu SQL và cách sửa.
6. Rào chắn chi phí bạn sẽ đặt ngày đầu tiên cho mỗi nền tảng là gì?

## Tài liệu

- Snowflake — Overview of warehouses (giá theo cỡ, tính theo giây): https://docs.snowflake.com/en/user-guide/warehouses-overview
- BigQuery — Pricing: https://cloud.google.com/bigquery/pricing
- BigQuery — Best practices for controlling costs: https://docs.cloud.google.com/bigquery/docs/best-practices-costs
- dbt — `run_results.json`: https://docs.getdbt.com/reference/artifacts/run-results-json
