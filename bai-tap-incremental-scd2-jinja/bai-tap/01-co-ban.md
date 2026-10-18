# 01 — Cơ bản: từ raw lên staging lên mart (B1–B8)

> Lý thuyết: [1.1 phân tầng](../../GD1-ly-thuyet/tuan-1/01-phan-tang-staging-intermediate-marts.md) · [2.4 test](../../GD1-ly-thuyet/tuan-2/04-custom-generic-tests.md)

**Tình huống:** ngày đầu đi làm. Bạn được cấp quyền đọc schema `raw` do team data platform nạp từ backend về. Chưa có model dbt nào. Nhiệm vụ: dựng tầng staging sạch, viết vài test, rồi làm bảng báo cáo đầu tiên.

Làm hết ở **ngày 0** (B5 có đoạn cần sang ngày 2–3). Xong B1–B8 mới sang [02-jinja.md](02-jinja.md).

⭐ cơ bản · ⭐⭐ trung bình

---

## B1 ⭐ Khám phá dữ liệu nguồn (không chấm)

Trước khi viết model, **luôn xem dữ liệu trước**.

```bash
dbt show --inline "select table_name from information_schema.tables where table_schema = 'raw' order by 1" --limit 20
dbt show --inline "describe raw.orders"
dbt show --inline "select * from raw.orders" --limit 10
dbt show --inline "select * from raw.products"
dbt show --inline "select * from raw.customers"
``` 

Trả lời (ghi ra giấy hoặc `lab/NOTES.md`):
1. Khoá chính của mỗi bảng là gì? Kiểm tra bằng `count(*)` so với `count(distinct ...)`.
2. Tiền đang lưu ở đơn vị nào?
3. Cột nào "bẩn"? (khoảng trắng thừa, chuỗi rỗng, hoa/thường lẫn lộn)
4. Cột nào cho biết dòng vào kho lúc nào? Khác gì `updated_at`?
5. Bảng nào **không có** `updated_at`?
6. `raw.events` có `event_id` trùng không?

<details><summary>Đáp án</summary>

1. `customers.customer_id`, `products.product_id`, `orders.order_id`, `order_items (order_id, line_no)`, `events.event_id` (về lý thuyết — từ ngày 2 sẽ bị trùng). `customer_changelog` là log, không có khoá đơn.
2. Cents (số nguyên): `amount_cents`, `list_price_cents`, `unit_price_cents`.
3. `products.product_name` có khoảng trắng hai đầu; `products.category` của sản phẩm 8 là `''`; `customers.email` của khách 2 có khoảng trắng và chữ hoa.
4. `_loaded_at`: lúc công cụ ingest ghi vào kho. `updated_at`: lúc dòng bị sửa ở hệ thống nguồn.
5. `products`.
6. Ngày 0 thì chưa. Hỏi lại câu này ở ngày 2.
</details>

---

## B2 ⭐ Khai báo sources

**Yêu cầu:** file `models/staging/_sources.yml` khai báo source tên `raw`, `schema: raw`, đủ 6 bảng: `customers`, `customer_changelog`, `products`, `orders`, `order_items`, `events`. Mỗi bảng 1 dòng `description`.

**Kiểm tra:**
```bash
dbt ls -s "source:*"          # phải liệt kê 6 source
python scripts/check.py B2    # PASS sau khi có ít nhất 1 model dùng source() (bài B3)
```

**Ngoài thực tế:** source là nơi duy nhất trong project được phép nhắc tới tên schema/bảng thô. Khi team platform đổi schema, bạn chỉ sửa đúng file này.

**Cách nhanh — sinh bằng codegen** (package `dbt-labs/codegen` đã có trong `packages.yml`):
```bash
dbt --quiet run-operation generate_source \
  --args '{"schema_name": "raw", "database_name": "lab", "generate_columns": true, "exclude": "_lab%"}' \
  > models/staging/_sources.yml
```
Sau đó tự thêm `description` cho từng bảng. Mở file kiểm tra lại: nếu lẫn dòng log thì xoá đi.

Lưu ý riêng cho DuckDB: dbt_utils (mà codegen dùng bên dưới) không có bản cài đặt `duckdb__get_tables_by_pattern_sql`, nên bản mặc định query `lab.information_schema.tables` và lỗi. Lab đã vá sẵn bằng `macros/duckdb__get_tables_by_pattern_sql.sql` + khối `dispatch` cuối `dbt_project.yml` — đọc hai chỗ đó, đây là ví dụ thật của `adapter.dispatch` (bài J9).

<details><summary>Gợi ý</summary>

```yaml
sources:
  - name: raw
    schema: raw
    tables:
      - name: orders
        description: Đơn hàng từ backend, ghi đè khi đổi trạng thái.
      ...
```
</details>

---

## B3 ⭐ `stg_orders` — model staging đầu tiên

**Yêu cầu:** `models/staging/stg_orders.sql`, materialized `view` (cấu hình cả folder trong `dbt_project.yml`: `staging: +materialized: view`).

Tên cột phải **đúng y như bảng dưới** — các bài sau và `check.py` dựa vào đây:

| Cột | Lấy từ | Xử lý |
|---|---|---|
| `order_id` | `order_id` | |
| `customer_id` | `customer_id` | |
| `order_date` | `order_date` | |
| `order_status` | `status` | đổi tên |
| `amount` | `amount_cents` | ÷ 100, làm tròn 2 chữ số |
| `updated_at` | `updated_at` | |
| `_loaded_at` | `_loaded_at` | giữ lại — cần cho incremental |

Viết theo mẫu CTE `source → renamed → select * from renamed`.

**Kiểm tra:** `dbt build -s stg_orders` → `check.py B3`.

**Câu hỏi:** vì sao staging thường là `view`? Vì sao đổi tên `status` ở staging chứ không đợi tới mart?

---

## B4 ⭐ Các model staging còn lại

**Yêu cầu:** 5 model, đều là view:

| Model | Cột (đúng tên) | Làm sạch |
|---|---|---|
| `stg_customers` | `customer_id, full_name, email, city, tier, updated_at, _loaded_at` | `trim` mọi chuỗi; `email`: `trim` + `lower`, chuỗi rỗng → `null` |
| `stg_customer_changelog` | `customer_id, op, full_name, email, city, tier, changed_at, _loaded_at` | như `stg_customers` |
| `stg_products` | `product_id, product_name, category, list_price, _loaded_at` | `trim`, chuỗi rỗng → `null`; `list_price` = cents ÷ 100 |
| `stg_order_items` | `order_id, line_no, product_id, quantity, unit_price, _loaded_at` | `unit_price` = cents ÷ 100 |
| `stg_events` | `event_id, user_id, event_type, event_ts, _loaded_at` | **không** dedupe (cố ý, để bài I1–I2 thấy dữ liệu trùng) |

**Kiểm tra:** `dbt build -s staging` → `check.py B4`.

**Ngoài thực tế:** staging là "hợp đồng" giữa dữ liệu nguồn và phần còn lại của project: mọi model phía sau chỉ đọc staging, không ai đọc `raw` nữa. Nguồn đổi gì, chỉ sửa ở đây (bạn sẽ thấy điều này rất rõ ở sự cố ngày 7).

<details><summary>Gợi ý</summary>

`nullif(lower(trim(email)), '')`. Ở bài J1–J2 bạn sẽ gom các biểu thức lặp lại này thành macro.
</details>

---

## B5 ⭐⭐ Test cơ bản — và lần đầu test đỏ

**Yêu cầu:** file `models/staging/_staging.yml`:

| Model.cột | Test |
|---|---|
| `stg_customers.customer_id` | `unique`, `not_null` |
| `stg_products.product_id` | `unique`, `not_null` |
| `stg_orders.order_id` | `unique`, `not_null` |
| `stg_orders.order_status` | `accepted_values`: placed, shipped, delivered, cancelled |
| `stg_orders.customer_id` | `relationships` tới `stg_customers.customer_id` |

**Kiểm tra:** `dbt build -s staging` (tất cả xanh) → `check.py B5`.

**Rồi cho thời gian trôi:**
```bash
python scripts/simulate.py next && dbt build -s staging     # ngày 1: xanh
python scripts/simulate.py next && dbt build -s staging     # ngày 2: test nào đỏ?
```

Ở ngày 2, test `relationships` đỏ. Điều tra:
```bash
dbt show --inline "select * from {{ ref('stg_orders') }} o where not exists (select 1 from {{ ref('stg_customers') }} c where c.customer_id = o.customer_id)"
```

Sang ngày 3: khách 11 đã xuất hiện, nhưng test vẫn đỏ — vì sao? (gợi ý: khách nào bị xoá ở ngày 3?)

**Quyết định của bạn:** test này nên `error` (chặn pipeline) hay `warn`? Đổi bằng:
```yaml
      - name: customer_id
        data_tests:
          - relationships:
              arguments:
                to: ref('stg_customers')
                field: customer_id
              config:
                severity: warn
```

**Thử thêm:** gắn `unique` cho `stg_events.event_id` rồi build ở ngày 2. Đỏ — đây là dữ liệu trùng mà bài I2 sẽ xử lý. Bỏ test đó đi (hoặc để `warn`), vì staging sự kiện được thiết kế không dedupe.

**Ngoài thực tế:**
- Fact đến trước dimension (*late-arriving dimension*) xảy ra hằng ngày: đơn tạo trước khi bảng khách kịp đồng bộ.
- Xoá cứng ở nguồn để lại "đơn mồ côi" vĩnh viễn.
- Test `error` trên staging sẽ **chặn mọi model phía sau** (chúng bị SKIP). Đó là lý do chọn severity cẩn thận.

Quay lại ngày 0 để làm tiếp: `python scripts/simulate.py reset && dbt build`.

---

## B6 ⭐⭐ Mart đầu tiên: `dim_products` và `fct_order_lines`

**Yêu cầu:** 2 model trong `models/marts/`, materialized `table` (cấu hình folder: `marts: +materialized: table`).

`dim_products` — 1 dòng / sản phẩm: `product_id, product_name, category, list_price`.

`fct_order_lines` — **grain: 1 dòng = 1 dòng đơn** `(order_id, line_no)`:

| Cột | Lấy từ |
|---|---|
| `order_id`, `line_no`, `product_id`, `quantity`, `unit_price` | `stg_order_items` |
| `order_date`, `customer_id`, `order_status` | `stg_orders` |
| `line_amount` | `quantity * unit_price` |

**Kiểm tra:** `dbt build -s marts` → `check.py B6`. Thêm test `dbt_utils.unique_combination_of_columns` cho `(order_id, line_no)`.

**Bẫy fan-out — thử ngay:**
```bash
dbt show --inline "select sum(o.amount) from {{ ref('stg_orders') }} o join {{ ref('stg_order_items') }} i using (order_id)"
dbt show --inline "select sum(amount) from {{ ref('stg_orders') }}"
```
Hai con số khác nhau. Vì sao? Đây là lỗi số 1 ngoài thực tế khi join bảng header với bảng chi tiết rồi `sum` cột của header.

**Câu hỏi:** dùng `left join` hay `inner join` giữa items và orders? Khi nào hai cách cho kết quả khác nhau?

---

## B7 ⭐⭐ `customer_lifetime` — và quy tắc nghiệp vụ đặt ở đâu

**Yêu cầu:** `customer_lifetime` (table), 1 dòng cho mỗi khách có ít nhất 1 **đơn tính doanh thu**:

| Cột | |
|---|---|
| `customer_id` | |
| `order_count` | số đơn tính doanh thu |
| `lifetime_value` | tổng `amount` các đơn tính doanh thu |
| `first_order_date`, `last_order_date` | trong các đơn tính doanh thu |

**Quy tắc "đơn tính doanh thu" hiện tại:** mọi đơn trừ `cancelled`.

**Thiết kế bắt buộc:** đặt quy tắc ở **một chỗ duy nhất** — model `models/intermediate/int_orders.sql` (view) = `stg_orders` + cột `is_revenue_order`. `customer_lifetime` (và sau này `fct_daily_revenue`) đọc từ `int_orders`.

**Kiểm tra:** `check.py B7` ở ngày 0, rồi `next` tới ngày 4 (có đơn bị huỷ) và kiểm tra lại.

**Ngoài thực tế:** "doanh thu" là định nghĩa bị đổi nhiều nhất trong công ty. Nếu mỗi model tự viết `where order_status <> 'cancelled'`, lần đổi quy tắc tiếp theo bạn sẽ quên sửa một chỗ — và hai dashboard ra hai con số. Giai đoạn sự cố sẽ đổi quy tắc này **hai lần**.

---

## B8 ⭐ View vs table và các lệnh chọn model (không chấm)

**Thử nghiệm:**
1. Ở ngày N, chạy `python scripts/simulate.py next` nhưng **chưa build**.
2. So số dòng:
   ```bash
   dbt show --inline "select count(*) from {{ ref('stg_orders') }}"       # view
   dbt show --inline "select count(*) from {{ ref('fct_order_lines') }}"  # table
   dbt show --inline "select count(*) from raw.orders"
   ```
   Model nào đã thấy dữ liệu mới, model nào chưa? Vì sao?
3. Thử các lệnh chọn model và đoán trước sẽ chạy những gì:
   ```bash
   dbt ls -s stg_orders+          # stg_orders và mọi thứ phía sau
   dbt ls -s +customer_lifetime   # customer_lifetime và mọi thứ phía trước
   dbt ls -s staging              # cả folder
   dbt ls -s tag:...              # (tự thêm tag cho vài model rồi thử)
   dbt build -s stg_orders+       # build + test phần bị ảnh hưởng khi sửa stg_orders
   ```
4. `dbt run`, `dbt test`, `dbt build` khác nhau thế nào? Khi test của `stg_orders` đỏ, `dbt build` làm gì với `customer_lifetime`?

---

✅ Xong B1–B8: `check.py B2 B3 B4 B5 B6 B7` đều PASS. Sang [02-jinja.md](02-jinja.md).
