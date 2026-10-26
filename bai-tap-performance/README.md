# Thực hành tuần 7: thí nghiệm hiệu năng và chi phí → performance playbook

Lý thuyết: [GĐ2 tuần 7](../GD2-ly-thuyet/README.md). Đầu ra: `docs/performance-playbook.md` điền từ [playbook-template.md](playbook-template.md) với **số đo thật** của bạn.

Khác với lab DuckDB, các thí nghiệm này chạy trên **Snowflake và BigQuery thật** (mô hình tính tiền là thứ cần học, DuckDB không mô phỏng được). Mọi script dùng dữ liệu mẫu có sẵn, không đụng dữ liệu của adventure_works.

## Chuẩn bị

| Nền tảng | Cần | Ghi chú |
|---|---|---|
| Snowflake | Tài khoản (adventure_works) hoặc **trial mới** | Trial: 30 ngày, kèm 400 USD credit (theo trang đăng ký; kiểm tra lại khi đăng ký). Đăng ký **đúng đầu tuần 7** để còn hạn |
| BigQuery | Project non-prod của tuần 5 | Dùng dataset riêng `perf_lab` |

Thời gian mỗi nền tảng khoảng 1 ngày. Chi phí ước tính: Snowflake vài credit (trong quota trial), BigQuery vài chục GB quét (trong 1 TiB miễn phí).

## An toàn chi phí (làm trước tiên)

- Snowflake: chạy `snowflake/00-setup.sql`: warehouse riêng `AUTO_SUSPEND = 60`, **resource monitor** giới hạn credit.
- BigQuery: chạy query trong project non-prod; mỗi query lớn, bấm xem dry run (góc phải editor) **trước** khi chạy. Có thể đặt "Maximum bytes billed" trong *Query settings* của console.

## Danh sách thí nghiệm

| # | File | Câu hỏi | Đo |
|---|---|---|---|
| S1 | [snowflake/01-pruning-va-clustering.sql](snowflake/01-pruning-va-clustering.sql) | Dữ liệu được sắp xếp giúp pruning bao nhiêu? | Partitions scanned / total, thời gian, `SYSTEM$CLUSTERING_INFORMATION` |
| S2 | [snowflake/02-query-profile-exploding-join-spill.sql](snowflake/02-query-profile-exploding-join-spill.sql) | Nhận ra exploding join và spilling trong Query Profile | Số dòng vào/ra của Join, bytes spilled |
| S3 | [snowflake/03-chon-co-warehouse.sql](snowflake/03-chon-co-warehouse.sql) | Cỡ warehouse nào đáng tiền cho một query nặng? | Thời gian × credit/giờ ở XS, S, M, L |
| S4 | [snowflake/04-theo-doi-chi-phi.sql](snowflake/04-theo-doi-chi-phi.sql) | Credit đi đâu? | Theo warehouse, theo `query_tag`, top query |
| B1 | [bigquery/01-partition-va-cluster.sql](bigquery/01-partition-va-cluster.sql) | Partition, cluster tiết kiệm bao nhiêu byte? | Byte xử lý (dry run) và byte tính tiền (JOBS) |
| B2 | [bigquery/02-incremental-merge-vs-insert-overwrite.md](bigquery/02-incremental-merge-vs-insert-overwrite.md) | Chiến lược incremental nào rẻ hơn cho `fct_events`? | `bytes_billed` trong `run_results.json` và JOBS theo label |
| B3 | [bigquery/03-do-chi-phi-jobs.sql](bigquery/03-do-chi-phi-jobs.sql) | Chi phí theo ngày, người dùng, model | `INFORMATION_SCHEMA.JOBS` |

Ghi mỗi thí nghiệm vào mục "Nhật ký thí nghiệm" của playbook theo mẫu: **câu hỏi → thay đổi (1 thứ) → trước → sau → kết luận**.

## Lưu ý khi đo

- **Tắt cache** khi đo thời gian Snowflake (`USE_CACHED_RESULT = FALSE`); suspend/resume warehouse nếu muốn xoá cả cache đĩa cục bộ (mỗi lần resume tính tối thiểu 60 giây).
- Chạy mỗi phép đo **2–3 lần**, lấy trung vị.
- Snowflake trial và BigQuery có thể chạy trên phần cứng khác nhau từng lúc: so sánh **tương đối** trong cùng một buổi, đừng so số tuyệt đối giữa các ngày.
- Các script **chưa được chạy thử** trên tài khoản thật (không có tài khoản để thử khi soạn). Câu lệnh theo tài liệu chính thức; gặp lỗi cú pháp thì đọc thông báo và đối chiếu link tài liệu ở đầu mỗi file.
