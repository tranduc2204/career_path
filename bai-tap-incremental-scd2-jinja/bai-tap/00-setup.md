# 00 — Cài đặt, dữ liệu và quy trình làm bài

## 1. Môi trường

`.venv/` đã được cài sẵn **dbt-core 1.12 + dbt-duckdb 1.11** (DuckDB 1.5). Nếu cần cài lại:

```bash
cd ~/Desktop/target_ae/bai-tap-incremental-scd2-jinja
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
```

`requirements.txt` ghim `dbt-core<2`. Lệnh `dbt --version` có thể in thông báo "dbt v2 is available" — bỏ qua, lab này dùng dbt Core v1 cho khớp roadmap.

Mỗi lần mở terminal mới:

```bash
cd ~/Desktop/target_ae/bai-tap-incremental-scd2-jinja
source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.
```

Lần đầu:

```bash
dbt deps
python scripts/simulate.py reset
dbt build
python scripts/check.py
```

## 2. Mô hình dữ liệu nguồn (schema `raw`)

Một shop online nhỏ. Tiền lưu bằng **cents** (số nguyên).

| Bảng | Khoá | Đặc điểm quan trọng |
|---|---|---|
| `customers` | `customer_id` | Nguồn **ghi đè**. Có `updated_at` nhưng có lúc nguồn **quên cập nhật**. Có thể bị xoá cứng. |
| `customer_changelog` | – | CDC log: mỗi insert/update/delete là 1 dòng (`op` = I/U/D), `changed_at` luôn đúng. |
| `products` | `product_id` | **Không có `updated_at`.** Giá bằng cents. Có tên chứa khoảng trắng thừa và category rỗng. |
| `orders` | `order_id` | Trạng thái `placed → shipped → delivered` (hoặc `cancelled`). Từ ngày 4 có thêm cột `channel`. |
| `order_items` | `order_id, line_no` | Dòng đơn. |
| `events` | `event_id` | Append-only. Có thể bị **gửi trùng** và **đến muộn**. |

Mọi bảng có `_loaded_at` = thời điểm công cụ ingest nạp/cập nhật dòng đó vào kho (giả lập Airbyte/Fivetran/dlt). Dòng nào bị sửa ở nguồn thì `_loaded_at` cũng đổi.

Staging (`models/staging/`) đã cho sẵn: rename `status → order_status`, đổi cents sang dollars (`amount`, `list_price`, `unit_price`). **Staging không dedupe sự kiện** — cố ý để bạn thấy dữ liệu trùng.

## 3. Kịch bản 6 ngày

`python scripts/simulate.py next` đẩy thời gian lên 1 ngày. Mỗi ngày nạp lúc 06:00 sáng hôm sau.

Quy tắc trạng thái mỗi ngày: đơn `placed` từ hôm trước → `shipped`; đơn `shipped` đủ 3 ngày tuổi → `delivered`.

| Ngày | `_loaded_at` | Chuyện gì xảy ra | Bài bị ảnh hưởng |
|---|---|---|---|
| **0** | 2026-01-01 06:00 | Nạp ban đầu: 10 khách, 8 sản phẩm, 30 đơn (27–31/12/2025), 90 sự kiện (29–31/12) | – |
| **1** | 2026-01-02 06:00 | Khách 3 chuyển **Ha Noi → Da Nang** (01-01 10:00). Sản phẩm 2 giảm giá **89.99 → 74.99**. 6 đơn mới ngày 01-01 | S1, S2, S6 |
| **2** | 2026-01-03 06:00 | Khách 2 **đổi email**. **3 đơn đến muộn**: `order_date` 2025-12-28, `updated_at` cũng là 2025-12-28, trạng thái delivered. **Đơn của khách 11** — khách này chưa tồn tại. **5 sự kiện bị gửi lại** (trùng `event_id`) | I1, I2, I3/I4, I5, S6 |
| **3** | 2026-01-04 06:00 | Khách 11 xuất hiện. Khách 5 lên hạng **silver → gold nhưng `updated_at` không đổi**. Khách 7 bị **xoá cứng**. Sản phẩm 5 đổi category. **6 sự kiện đến muộn** (`event_ts` ngày 01-01) | S3, S4, S5, S6, S7, I6 |
| **4** | 2026-01-05 06:00 | **`raw.orders` thêm cột `channel`**. **Huỷ 2 đơn** ngày 01-03. Khách 3 chuyển **Da Nang → Ho Chi Minh** (01-04 10:00) | I5, I7, J4, S1 |
| **5** | 2026-01-06 06:00 | Khách 8 lên hạng. Sản phẩm 2 **tăng giá trở lại 89.99**. Sản phẩm 9 mới. **2 đơn đến muộn** ngày 01-01 (trễ 4 ngày). **4 sự kiện gửi lại** | I3/I4, I5, S1, S2 |

Xem lại những gì đã xảy ra: `python scripts/simulate.py status`.

## 4. Quy trình làm bài

### Vòng lặp hằng ngày

```bash
python scripts/simulate.py next                  # sang ngày mới
dbt build --exclude fct_events_microbatch        # build + test + snapshot
python scripts/check.py                          # chấm tất cả (hoặc: check.py I3 S1)
```

`fct_events_microbatch` (bài I8) được loại ra vì nó cần chạy với khoảng ngày cụ thể — xem đề I8.

### Khi sửa logic

| Bạn sửa | Làm gì |
|---|---|
| Model incremental | `dbt build -s <model> --full-refresh` (raw còn đủ lịch sử nên tính lại được) |
| Snapshot hoặc SCD2 tự viết (S1–S7) | `./scripts/replay.sh` — reset và chạy lại từng ngày, vì lịch sử đã bỏ lỡ **không lấy lại được** |
| Chỉ muốn thử tới một ngày | `./scripts/replay.sh 3` |

`replay.sh` dùng `python` và `dbt` trong PATH — nhớ `source .venv/bin/activate` trước.

### Các lệnh simulate

| Lệnh | Tác dụng |
|---|---|
| `reset` | **Xoá toàn bộ `lab.duckdb`** (cả model, snapshot), nạp ngày 0 |
| `next` | Sang ngày kế tiếp |
| `status` | Đang ở ngày nào, đã xảy ra gì |
| `goto N` | Reset rồi nhảy thẳng tới ngày N. Snapshot sẽ **không** thấy các ngày ở giữa (dùng cho bài S8) |

### Xem dữ liệu

```bash
dbt show --inline "select * from raw.orders order by order_id desc" --limit 10
dbt show --inline "select * from {{ ref('fct_orders') }} where customer_id = 3"
dbt show -s fct_daily_revenue --limit 20
```

Có thể mở `lab.duckdb` bằng DBeaver, nhưng **DuckDB chỉ cho một tiến trình ghi tại một thời điểm**: đóng DBeaver trước khi chạy dbt/simulate, nếu không sẽ gặp lỗi "Could not set lock on file".

## 5. Cú pháp cần biết với dbt 1.10+

Tham số của generic test đặt dưới `arguments:` (cách cũ vẫn chạy nhưng báo deprecation):

```yaml
data_tests:
  - is_positive:
      arguments:
        allow_zero: true
```

Snapshot khai báo bằng YAML trong `snapshots/*.yml` với `relation:` (dbt ≥ 1.9), không cần block `{% snapshot %}`.

## 6. Lỗi hay gặp khi setup

| Lỗi | Cách sửa |
|---|---|
| `Could not find profile named 'lab'` | Quên `export DBT_PROFILES_DIR=.` hoặc không đứng trong `lab/` |
| `Could not set lock on file lab.duckdb` | Đóng DBeaver / tiến trình dbt khác |
| `dbt_utils is undefined` | Chưa `dbt deps` |
| `check.py` toàn SKIP sau khi viết model | Chưa `dbt build`, hoặc tên model khác tên trong đề |
