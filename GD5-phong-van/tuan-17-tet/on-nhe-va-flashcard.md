# Tuần 17 (4–10/2/2027): Tết, ôn nhẹ

> Tết Nguyên Đán 6/2/2027 (thứ Bảy). Tuần này **không học mới**. Mục tiêu: giữ nhịp, không quên, và nghỉ thật để sau Tết vào guồng phỏng vấn.

## Lịch gợi ý (≤ 1–2 giờ/ngày, có ngày nghỉ hẳn)

| Ngày | Việc (tối đa) |
|---|---|
| T5 04/2 | 30 phút: 20 flashcard bên dưới. 30 phút: sửa CV theo phản hồi đợt nộp tháng 1 |
| T6 05/2 (28 Tết) | 30 phút: nghe lại 1 bản ghi mock system design, ghi 3 điểm cải thiện |
| T7 06/2 (Mùng 1) | Nghỉ |
| CN 07/2 | Nghỉ |
| T2 08/2 | 30 phút: 20 flashcard tiếp. Kể thành tiếng 2 câu chuyện STAR |
| T3 09/2 | 45 phút: một đề system design ngắn (D-series, 30 phút), không chấm kỹ |
| T4 10/2 | 1 giờ: chuẩn bị đợt nộp sau Tết: danh sách 15 công ty, CV theo từng loại, lịch tuần 18 |

Nếu Tết ở quê, không có máy: in flashcard ra giấy, hoặc mở trên điện thoại.

## 60 flashcard (đọc câu hỏi, tự trả lời thành tiếng, rồi mới xem đáp án)

<details><summary><b>dbt (1–20)</b></summary>

| # | Hỏi | Đáp |
|---|---|---|
| 1 | Materialization mặc định? | `view` |
| 2 | `is_incremental()` đúng khi? | Bảng đích tồn tại dạng table, model incremental, không `--full-refresh` |
| 3 | `on_schema_change` mặc định? | `ignore` |
| 4 | Microbatch cần config gì? | `event_time`, `batch_size`, `begin` (+ `lookback`, mặc định 1) |
| 5 | Backfill microbatch? | `--event-time-start` / `--event-time-end` |
| 6 | Slim CI? | `dbt build -s state:modified+ --defer --state <prod>` |
| 7 | `--defer` làm gì? | Ref tới node không chọn và chưa có ở môi trường hiện tại → dùng bản của state (prod) |
| 8 | `dbt retry`? | Chạy lại node lỗi + bị skip của lần trước (đọc `run_results.json`) |
| 9 | `dbt clone`? | Clone (zero-copy hoặc view) node từ môi trường trong state sang target hiện tại |
| 10 | Contract bắt buộc gì? | Mọi cột khai báo + `data_type`; lỗi trước khi thay bảng |
| 11 | Snowflake thực thi constraint nào? | Chỉ `not_null` |
| 12 | `ref('m')` khi có versions? | `latest_version` |
| 13 | access mặc định? | `protected` |
| 14 | Test fail trong `build` thì? | Node phía sau bị skip |
| 15 | `warn_if: >0, error_if: >100`, 25 dòng lỗi? | warn |
| 16 | Unit test chạy khi nào trong build? | Trước khi build model |
| 17 | `target/compiled` vs `target/run`? | SELECT sau Jinja vs câu thật có DDL |
| 18 | Selector `@m`? | m + con cháu + tổ tiên của con cháu |
| 19 | Dấu phẩy trong selector? | Giao (AND) |
| 20 | Freshness ghi ra đâu? | `target/sources.json` |
</details>

<details><summary><b>Mô hình dữ liệu (21–35)</b></summary>

| # | Hỏi | Đáp |
|---|---|---|
| 21 | 4 bước Kimball? | Quy trình nghiệp vụ → grain → dimension → fact |
| 22 | Semi-additive là gì, ví dụ? | Cộng theo một số chiều, không theo thời gian: số dư, tồn kho |
| 23 | 3 loại fact chính? | Transaction, periodic snapshot, accumulating snapshot (+ factless) |
| 24 | SCD2 cần cột gì? | surrogate key theo phiên bản, durable key, valid_from, valid_to, is_current |
| 25 | Inferred member? | Fact đến trước dimension → tạo dòng dim tạm, cập nhật khi dim về |
| 26 | Bridge table dùng khi? | Nhiều–nhiều (khách đồng sở hữu tài khoản, đơn nhiều voucher) |
| 27 | Hub / link / satellite? | Business key / quan hệ / thuộc tính có lịch sử |
| 28 | Khi nào chọn Data Vault? | Nhiều nguồn chồng lấn, nguồn đổi nhiều, cần audit lịch sử |
| 29 | Bitemporal? | Valid time (xảy ra khi nào) + transaction time (kho biết khi nào) |
| 30 | As-reported vs restated? | Số đã nộp giữ nguyên vs số đúng nhất hiện tại |
| 31 | Fan-out? | Join 1-nhiều rồi tổng hợp → nhân dòng, số phình |
| 32 | Ratio metric đúng ở mọi grain vì? | Tính tử và mẫu ở grain được hỏi rồi mới chia |
| 33 | Conformed dimension? | Một dimension dùng chung cho nhiều fact để drill-across |
| 34 | Late-arriving fact xử lý? | Incremental lookback, gán đúng phiên bản dim theo thời điểm sự kiện |
| 35 | Idempotent nghĩa là? | Chạy lại cùng đầu vào ra cùng kết quả |
</details>

<details><summary><b>Nền tảng (36–50)</b></summary>

| # | Hỏi | Đáp |
|---|---|---|
| 36 | SLI / SLO / SLA? | Thứ đo / mục tiêu nội bộ / cam kết với người dùng |
| 37 | Freshness theo `_loaded_at` sai khi? | Bảng ít đổi / thưa → báo động giả; dùng sync log |
| 38 | Anomaly vs test luật? | Thống kê, học từ lịch sử vs điều kiện biết trước, chắc chắn |
| 39 | Severity error trên source? | Chặn cả nhánh phía sau |
| 40 | Model contract vs data contract? | Giao diện model dbt vs thoả thuận với đội nguồn (schema, SLA, quy trình đổi) |
| 41 | Task-centric vs asset-centric? | Chạy lệnh gì vs bảng nào, cập nhật lúc nào |
| 42 | Cosmos `DBT_MANIFEST`? | Parse DAG từ manifest, không gọi dbt khi scheduler đọc DAG |
| 43 | Chi phí BigQuery on-demand tính theo? | TB quét (~6,25 USD/TiB) |
| 44 | Snowflake XS/S/M credit/giờ? | 1 / 2 / 4 |
| 45 | 3 tầng che PII? | dbt (build), warehouse (masking policy / policy tag), BI |
| 46 | Blue-green deploy với Snowflake? | Build schema mới rồi `ALTER SCHEMA ... SWAP WITH` |
| 47 | Ref chéo project trên dbt Core? | `dbt-loom` (platform có sẵn) |
| 48 | Khi nào tách dbt Mesh? | Ranh giới domain ổn định, giao diện rõ, cần deploy/quyền độc lập |
| 49 | Context engineering cho AI số liệu? | Hỏi qua semantic layer + metadata + glossary + tool + đánh giá |
| 50 | Lambda architecture? | Luồng nhanh (tạm tính) + luồng batch (chính thức), đối soát |
</details>

<details><summary><b>Ngân hàng / tài chính (51–60)</b></summary>

| # | Hỏi | Đáp |
|---|---|---|
| 51 | EOD? | End-of-day batch của core: chốt sổ ngày, tính lãi, phí |
| 52 | Value date vs booking date? | Ngày có hiệu lực vs ngày ghi sổ (có thể lùi ngày) |
| 53 | Đối soát GL? | Tổng số dư tài khoản (từ kho) vs số dư sổ cái theo ngày × sản phẩm × tiền tệ |
| 54 | CDC op? | r/c/u/d (snapshot, create, update, delete), sắp theo lsn/SCN |
| 55 | Reversal? | Giao dịch đảo: trạng thái đổi, không xoá; loại khỏi số dư |
| 56 | Nhóm nợ theo DPD (tham khảo TT 11/2021)? | 1 <10 ngày, 2 10–89, 3 90–179, 4 180–359, 5 ≥360; nợ xấu = 3–5 |
| 57 | Tỉ lệ nợ xấu là loại metric gì? | Ratio: Σ dư nợ nhóm 3–5 / Σ dư nợ |
| 58 | Tỷ giá ngày nghỉ? | Forward-fill tỷ giá gần nhất trước đó, lưu tỷ giá đã dùng |
| 59 | Kỳ đã khoá sổ có giao dịch lùi? | Không sửa as-reported, ghi điều chỉnh kỳ sau |
| 60 | Báo cáo cơ quan quản lý cần gì đặc biệt? | Tái lập được, audit, không phát hành khi còn lệch đối soát chưa giải thích |
</details>
