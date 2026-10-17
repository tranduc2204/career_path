# 00 — Cài đặt, dữ liệu và quy trình làm bài

## 1. Môi trường

Folder này là một uv project (`pyproject.toml`) ghim **dbt-core 1.x + dbt-duckdb 1.x**. Cài hoặc cài lại:

```bash
cd ~/Desktop/target_ae/bai-tap-incremental-scd2-jinja
uv sync                      # tạo/cập nhật .venv theo pyproject.toml
```

Lệnh `dbt --version` có thể in "dbt v2 is available" — bỏ qua, lab này dùng dbt Core v1 cho khớp roadmap.

Mỗi lần mở terminal mới:

```bash
cd ~/Desktop/target_ae/bai-tap-incremental-scd2-jinja
source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.          # profiles.yml nằm ngay trong lab/
```

Lần đầu:

```bash
dbt deps                           # cài dbt_utils
python scripts/simulate.py reset   # tạo lab.duckdb, nạp dữ liệu ngày 0
python scripts/check.py            # tất cả SKIP — bạn chưa viết gì
```

`lab/` **không có sẵn model nào**. Bạn tự xây từ staging lên, bắt đầu ở [01-co-ban.md](01-co-ban.md).

## 2. Dữ liệu nằm ở đâu

Mọi thứ nằm trong một file: `lab/lab.duckdb`.

```
lab.duckdb
├── raw      ← dữ liệu nguồn do scripts/simulate.py ghi (giả lập hệ thống backend + công cụ ingest)
├── dev      ← model/snapshot dbt build ra (target dev trong profiles.yml)
└── ...      ← thêm schema khác nếu bạn làm bài J6
```

`profiles.yml` dùng `path: lab.duckdb` (đường dẫn tương đối) → **luôn chạy dbt từ trong `lab/`**.

## 3. Mô hình dữ liệu nguồn (schema `raw`)

Một shop online nhỏ. Tiền lưu bằng **cents** (số nguyên).

| Bảng | Khoá | Đặc điểm |
|---|---|---|
| `customers` | `customer_id` | Nguồn **ghi đè** (chỉ giữ trạng thái hiện tại). Có `updated_at`. |
| `customer_changelog` | – | CDC log: mỗi insert/update/delete khách là 1 dòng (`op` = I/U/D, `changed_at`). |
| `products` | `product_id` | **Không có `updated_at`.** Giá bằng cents. |
| `orders` | `order_id` | Trạng thái `placed → shipped → delivered` (hoặc `cancelled`). |
| `order_items` | `order_id, line_no` | Dòng đơn. |
| `events` | `event_id` | Sự kiện web, append-only. |

Mọi bảng có `_loaded_at` = thời điểm công cụ ingest nạp/cập nhật dòng đó vào kho. Dòng nào bị sửa ở nguồn (qua đường bình thường) thì `_loaded_at` cũng đổi.

## 4. Dòng thời gian: 12 ngày, 2 giai đoạn

`python scripts/simulate.py next` đẩy thời gian lên 1 ngày. Mỗi ngày nạp lúc 06:00 sáng hôm sau.

Quy tắc trạng thái mỗi ngày: đơn `placed` từ hôm trước → `shipped`; đơn `shipped` đủ 3 ngày tuổi → `delivered`.

### Giai đoạn xây dựng (ngày 0–5): kịch bản công khai

| Ngày | `_loaded_at` | Chuyện gì xảy ra | Bài bị ảnh hưởng |
|---|---|---|---|
| **0** | 2026-01-01 06:00 | Nạp ban đầu: 10 khách, 8 sản phẩm, 30 đơn (27–31/12/2025), 90 sự kiện | – |
| **1** | 2026-01-02 06:00 | Khách 3 chuyển **Ha Noi → Da Nang**. Sản phẩm 2 giảm giá **89.99 → 74.99**. Đơn mới | S1, S2, S6 |
| **2** | 2026-01-03 06:00 | Khách 2 **đổi email**. **3 đơn đến muộn** (`order_date` 28/12). **Đơn của khách 11** — khách này chưa tồn tại. **5 sự kiện bị gửi lại** | B5, I1–I5, S6 |
| **3** | 2026-01-04 06:00 | Khách 11 xuất hiện. Khách 5 lên hạng **nhưng `updated_at` không đổi**. Khách 7 bị **xoá cứng**. **6 sự kiện đến muộn** | B5, S3–S7, I6 |
| **4** | 2026-01-05 06:00 | **`raw.orders` thêm cột `channel`**. **Huỷ 2 đơn**. Khách 3 chuyển **Da Nang → Ho Chi Minh** | B7, I5, I7, J4, S1 |
| **5** | 2026-01-06 06:00 | Khách 8 lên hạng. Sản phẩm 2 **tăng giá lại 89.99**. Sản phẩm 9 mới. **2 đơn đến muộn 4 ngày**. **4 sự kiện gửi lại** | I3, I5, S1, S2 |

### Giai đoạn vận hành (ngày 6–11): sự cố production — bị giấu

Hệ thống đã ổn định, mỗi ngày vẫn chạy bình thường, nhưng **mỗi ngày nguồn gây ra một sự cố** giống ngoài thực tế. Khi `next`, script chỉ báo 🚨 *"Có chuyện bất thường"* — bạn phải tự điều tra từ lỗi build, test, `check.py` và dữ liệu. Đề ở [05-su-co-thuc-te.md](05-su-co-thuc-te.md).

Chỉ khi bí: `python scripts/simulate.py status --reveal`.

## 5. Quy trình làm bài

### Vòng lặp hằng ngày

```bash
python scripts/simulate.py next                  # sang ngày mới
dbt build --exclude fct_events_microbatch        # build + test + snapshot
python scripts/check.py                          # chấm tất cả (hoặc: check.py B3 I3)
```

`fct_events_microbatch` (bài I8) được loại ra vì cần chạy với khoảng ngày cụ thể — xem đề I8.

### Khi sửa logic

| Bạn sửa | Làm gì |
|---|---|
| Staging / model `table` | `dbt build -s <model>+` |
| Model incremental | `dbt build -s <model> --full-refresh` (raw còn đủ lịch sử nên tính lại được) |
| Snapshot hoặc SCD2 tự viết | `./scripts/replay.sh` — reset và chạy lại từng ngày, vì lịch sử đã bỏ lỡ **không lấy lại được** |
| Muốn thử tới một ngày | `./scripts/replay.sh 3` (mặc định chạy tới ngày 5; `replay.sh 11` chạy cả giai đoạn sự cố) |

### Runbook (giai đoạn sự cố)

Có sự cố cần thao tác vận hành ngoài `dbt build` (vd backfill)? Ghi thao tác đó vào `scripts/hooks/after_day_<N>.sh` (nhớ `chmod +x`). `replay.sh` tự chạy file này ngay sau build của ngày N → lần replay sau bạn không phải nhớ làm tay. Đây chính là *runbook dưới dạng code*.

### Các lệnh simulate

| Lệnh | Tác dụng |
|---|---|
| `reset` | **Xoá toàn bộ `lab.duckdb`** (cả model, snapshot), nạp ngày 0 |
| `next` | Sang ngày kế tiếp |
| `status` | Đang ở ngày nào, đã xảy ra gì (sự cố bị ẩn) |
| `status --reveal` | Hiện cả chi tiết sự cố |
| `goto N` | Reset rồi nhảy thẳng tới ngày N. Snapshot sẽ **không** thấy các ngày ở giữa (dùng cho bài S8) |

### Xem dữ liệu

```bash
dbt show --inline "select * from raw.orders order by order_id desc" --limit 10
dbt show --inline "select * from {{ ref('stg_orders') }} where customer_id = 3"
dbt show -s fct_daily_revenue --limit 20
```

Có thể mở `lab.duckdb` bằng DBeaver, nhưng **DuckDB chỉ cho một tiến trình ghi tại một thời điểm**: ngắt kết nối DBeaver trước khi chạy dbt/simulate, nếu không sẽ gặp lỗi "Could not set lock on file".

## 6. Cú pháp cần biết với dbt 1.10+

Tham số của generic test đặt dưới `arguments:` (cách cũ vẫn chạy nhưng báo deprecation):

```yaml
data_tests:
  - accepted_values:
      arguments:
        values: ["placed", "shipped"]
      config:
        severity: warn
```

Snapshot khai báo bằng YAML trong `snapshots/*.yml` với `relation:` (dbt ≥ 1.9), không cần block `{% snapshot %}`.

## 7. Lỗi hay gặp khi setup

| Lỗi | Cách sửa |
|---|---|
| `Could not find profile named 'lab'` | Quên `export DBT_PROFILES_DIR=.` hoặc không đứng trong `lab/` |
| `Could not set lock on file lab.duckdb` | Đóng DBeaver / tiến trình dbt khác |
| `dbt_utils is undefined` | Chưa `dbt deps` |
| `check.py` toàn SKIP sau khi viết model | Chưa `dbt build`, hoặc tên model/cột khác tên trong đề |
