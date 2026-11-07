# 11.4 Đáp án đề thi thử

> Chấm xong, ghi số câu sai theo mảng vào bảng cuối file. Mảng nào < 70% thì đọc lại phần tương ứng ở [11.2](02-on-thi-theo-chu-de.md) và docs.

| Câu | Đáp án | Giải thích |
|---|---|---|
| 1 | B | `view` là mặc định |
| 2 | A, C | Cần: bảng đích tồn tại **dưới dạng table**, model là incremental, **không** `--full-refresh` |
| 3 | C | `on_schema_change` mặc định là `ignore`: cột mới không được thêm vào bảng đích |
| 4 | D | `insert_overwrite` thay cả partition (BigQuery, Spark/Databricks) |
| 5 | B | `lookback` xử lý lại N lô trước lô hiện tại để đón dữ liệu đến trễ |
| 6 | C | Upstream có `event_time` được tự lọc theo cửa sổ của lô (không muốn thì `.render()`) |
| 7 | B | `--event-time-start` / `--event-time-end` |
| 8 | B | `--empty` giới hạn ref/source về 0 dòng: kiểm tra SQL và schema mà không tốn chi phí |
| 9 | C | `relation: ref(...)` hoặc `relation: source(...)` |
| 10 | B | `check` cần `check_cols` (danh sách hoặc `all`). `updated_at` dành cho `timestamp` |
| 11 | C | `config()` trong model ưu tiên nhất, rồi tới YAML properties, rồi `dbt_project.yml` |
| 12 | B | Python model: `def model(dbt, session)` trả DataFrame; chỉ một số adapter; dùng `dbt.ref()` (không Jinja); SQL model vẫn `ref` được nó |
| 13 | B | `persist_docs: {relation: true, columns: true}` |
| 14 | A | Doc block trong file `.md` |
| 15 | A, C | Ephemeral thành CTE; không có contract. Không tạo view, không phải mặc định |
| 16 | B | Contract kiểm tra trước (preflight), lỗi thì không thay bảng cũ |
| 17 | B | Snowflake chỉ thực thi `not_null`; PK/unique/FK là metadata → vẫn cần test `unique` |
| 18 | B | `ref` không ghim version → `latest_version` |
| 19 | C | `<model>_v<version>` |
| 20 | C | Cảnh báo deprecation; không tự xoá, không chặn |
| 21 | B | Đổi tên / xoá cột / đổi kiểu là phá vỡ. Thêm cột không phá vỡ |
| 22 | B, C | Contract + incremental chỉ hỗ trợ `append_new_columns` và `fail` |
| 23 | B | `ref` tới node không tồn tại → compilation error lúc parse/compile, trước khi chạy SQL |
| 24 | B | `target/run/` có câu thật kèm DDL. `target/compiled/` chỉ có SELECT sau Jinja |
| 25 | A | Lúc parse `execute` là False, `run_query` trả None → bọc bằng `{% if execute %}` |
| 26 | B | `dbt debug` |
| 27 | B | `log(msg, info=True)` in ra console |
| 28 | B | `flags:` trong `dbt_project.yml` để bật/tắt hành vi mới trong giai đoạn chuyển tiếp |
| 29 | B | Jinja sai cú pháp → compilation error lúc render, chưa gửi SQL nào. (Bẫy liên quan đã đo trên dbt-core 1.12.6: gõ sai khoá YAML như `colums:` thì dbt **không báo gì**, test cột bên dưới lặng lẽ biến mất → so số test trong `dbt ls -s test_type:data` trước/sau) |
| 30 | A | Tên model phải duy nhất trong project (khác package thì được) |
| 31 | B | Test error trong `build` → node phía sau bị skip |
| 32 | B | `dbt retry` dùng `run_results.json`, chạy lại node lỗi + bị skip với cùng lệnh/cờ |
| 33 | B | Clone (zero-copy nếu có, không thì view) từ môi trường trong state sang target hiện tại |
| 34 | B | Mặc định không tạo lại relation đã có; `--full-refresh` để ghi đè |
| 35 | B | Dừng ngay khi có node lỗi |
| 36 | B | Lỗi dữ liệu không tự hết khi retry. Điều tra (store_failures), xử lý nguồn |
| 37 | B | `run_results.json` |
| 38 | B | Trả về dòng lỗi; 0 dòng là pass |
| 39 | A | `{% test %}` trong `tests/generic/` (hoặc macros), hoặc macro tên `test_<tên>` |
| 40 | B | File `.sql` trong `tests/` trả về dòng lỗi |
| 41 | B | 25 > 0 → warn; 25 không > 100 → không error |
| 42 | A | Lưu dòng lỗi vào bảng (schema `_dbt_test__audit` mặc định) |
| 43 | A, C | Unit test kiểm logic với input giả, khai báo `unit_tests:` + `given`/`expect`. Không cho Python model, không kiểm dữ liệu thật |
| 44 | A | `test_type:unit` (ngược lại `test_type:data`) |
| 45 | B | Unit test chạy trước khi build model đó |
| 46 | A, B, C | `dict`, `csv`, `sql` |
| 47 | B | `arguments:` (dbt ≥ 1.10) |
| 48 | A, B, C, D | `accepted_range` là của `dbt_utils` |
| 49 | B | 18h > 12h (warn), < 24h (chưa error) |
| 50 | B | `target/sources.json` |
| 51 | A, B, D | `dashboard`, `notebook`, `analysis`, `ml`, `application` |
| 52 | B | `owner` (cần name hoặc email) là bắt buộc. `type` và `name` cũng bắt buộc |
| 53 | B | `+exposure:x`: mọi thứ exposure phụ thuộc |
| 54 | C | `package-lock.yml` |
| 55 | A | `dispatch` + `search_order` |
| 56 | A | Slim CI chuẩn |
| 57 | B | Trỏ sang relation của môi trường trong manifest của `--state` |
| 58 | A | Ưu tiên bản prod kể cả khi node đã có ở môi trường hiện tại |
| 59 | B | `manifest.json` |
| 60 | A | `result:error+` (cần `--state` trỏ tới artifact của lần trước) |
| 61 | B | `state:modified` gồm `.macros`: đổi macro thì model dùng nó được chọn |
| 62 | A, B, D | Có `.body`, `.configs`, `.relation`, `.persisted_descriptions`, `.macros`, `.contract`. Không có `.owner` |
| 63 | A | Nguồn có dữ liệu mới hơn lần đo freshness trước (trong `--state`) + con cháu |
| 64 | B | `@m` |
| 65 | B | Dấu phẩy là **giao** (AND); dấu cách là hợp (OR) |

## Tự đánh giá theo mảng

| Mảng | Câu | Đúng / tổng | % |
|---|---|---|---|
| 1. Developing models | 1–15 | /15 | |
| 2. Governance | 16–22 | /7 | |
| 3. Debugging | 23–30 | /8 | |
| 4. Pipelines | 31–37 | /7 | |
| 5. Tests | 38–48 | /11 | |
| 6. External dependencies | 49–55 | /7 | |
| 7. State | 56–65 | /10 | |
| **Tổng** | | **/65** | |

Câu nào **đoán đúng** cũng tính là sai khi ôn lại.
