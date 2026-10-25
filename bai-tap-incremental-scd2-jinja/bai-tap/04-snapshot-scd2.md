# 04 — Snapshot & SCD2 (S1–S8)

> Lý thuyết: [2.3 snapshots](../../GD1-ly-thuyet/tuan-2/03-snapshots-scd2.md)

## Đọc trước khi làm

- Snapshot chỉ ghi lại **trạng thái tại lúc nó chạy**. Muốn có lịch sử đúng, snapshot phải chạy **từ ngày 0 và sau mỗi ngày**. Lỡ một ngày là mất, không lấy lại được.
- Vì vậy mỗi khi tạo hoặc sửa snapshot / SCD2 tự viết: dùng `./scripts/replay.sh` (reset và chạy lại từng ngày).
- `dbt build` chạy cả snapshot (đúng thứ tự DAG). Chạy riêng: `dbt snapshot`.
- Khai báo snapshot bằng YAML trong `snapshots/` (dbt ≥ 1.9):

```yaml
snapshots:
  - name: snap_xxx
    relation: ref('stg_xxx')
    config:
      unique_key: ...
      strategy: timestamp   # hoặc check
      ...
```

---

## S1 ⭐⭐ Snapshot `timestamp`

**Yêu cầu:** `snap_customers` từ `stg_customers`, `strategy: timestamp`, `updated_at: updated_at`.

**Làm:** `./scripts/replay.sh` rồi xem lịch sử khách 3:
```bash
dbt show --inline "select customer_id, city, dbt_valid_from, dbt_valid_to from {{ ref('snap_customers') }} where customer_id = 3 order by dbt_valid_from"
```

**Kiểm tra:** `check.py S1`.

**Câu hỏi suy ngẫm**
1. `dbt_valid_from` của các phiên bản lấy từ đâu? Là thời gian nghiệp vụ hay thời gian chạy?
2. Khách 2 chỉ đổi email mà vẫn có phiên bản mới. Có phải lúc nào cũng muốn vậy?

---

## S2 ⭐⭐ Snapshot `check`

**Yêu cầu:** `snap_products` từ `stg_products`, `strategy: check`, `check_cols: [product_name, category, list_price]`. Gắn test `one_current_row_per_key` (J5) cho `product_id`.

**Kiểm tra:** `check.py S2`. Sản phẩm 2 phải có **3** phiên bản (giá 89.99 → 74.99 → 89.99).

**Quan sát quan trọng:** xem `dbt_valid_from` của `snap_products`. Đó là ngày giờ **thật** lúc bạn chạy lệnh (2026-10-...), không phải ngày nghiệp vụ 01/2026.

**Câu hỏi suy ngẫm**
1. Vì sao `check` không thể biết thời điểm thay đổi thật?
2. Hệ quả: bạn có join được "giá sản phẩm tại ngày đặt đơn" từ `snap_products` không? Trong production (snapshot chạy mỗi đêm), sai số là bao nhiêu?
3. Giá quay về giá cũ vẫn tạo phiên bản mới — đúng hay sai về mặt nghiệp vụ?

--- 

## S3 ⭐⭐⭐ Bẫy `updated_at`

**Bối cảnh:** ngày 3, khách 5 lên hạng silver → gold nhưng nguồn **quên cập nhật `updated_at`**.

**Yêu cầu**
1. Sau replay tới ngày 5: xem `snap_customers` của khách 5. Có phiên bản gold không?
2. Tạo `snap_customers_check`: `strategy: check`, `check_cols: [city, tier]`.
3. So sánh 2 snapshot cho khách 2, 3, 5.

**Kiểm tra:** `check.py S3`.

**Câu hỏi suy ngẫm**
1. Điền bảng:

   | | `timestamp` (S1) | `check [city, tier]` (S3) |
   |---|---|---|
   | Khách 2 đổi email | ? | ? |
   | Khách 5 đổi hạng, không đổi updated_at | ? | ? |
   | Biết thời điểm thay đổi thật | ? | ? |

2. Viết một câu SQL phát hiện "nghi ngờ `updated_at` không đáng tin": so 2 snapshot, tìm khách mà `snap_customers_check` có nhiều phiên bản hơn `snap_customers`.
3. Trong thực tế bạn chọn strategy nào cho bảng customers? Vì sao?

---

## S4 ⭐⭐⭐ Hard deletes

**Bối cảnh:** ngày 3, khách 7 bị xoá cứng khỏi nguồn.

**Yêu cầu**
- `snap_customers`: `hard_deletes: invalidate`
- `snap_customers_check`: `hard_deletes: new_record`
- Replay. Xem các dòng của khách 7 trong cả 2 snapshot.

**Kiểm tra:** `check.py S4`.

**Câu hỏi suy ngẫm**
1. `invalidate` và `new_record` khác nhau thế nào? Cột nào xuất hiện thêm với `new_record`?
2. `dbt_valid_to` của dòng bị đóng là thời gian nào?
3. Nếu bật `hard_deletes` **sau** ngày 3 (không replay), chuyện gì xảy ra với khách 7?

---

## S5 ⭐⭐⭐ `dim_customers` SCD2

**Yêu cầu:** `models/marts/dim_customers.sql` từ `snap_customers`:

| Cột | Cách tính |
|---|---|
| `customer_sk` | `dbt_utils.generate_surrogate_key(['customer_id', 'dbt_valid_from'])` |
| `customer_id`, `full_name`, `email`, `city`, `tier` | |
| `valid_from` | `dbt_valid_from` |
| `valid_to` | `dbt_valid_to`, null → `9999-12-31` |
| `is_current` | `dbt_valid_to is null` |

Thêm 1 dòng **unknown member**: `customer_sk = '-1'`, `customer_id = -1`, city/tier = `'Unknown'`, hiệu lực 1900-01-01 → 9999-12-31.

Test trong YAML:
- `customer_sk`: `unique`, `not_null`
- `customer_id`: `one_current_row_per_key` với `current_condition: is_current`
- Model: `dbt_utils.mutually_exclusive_ranges` (valid_from, valid_to, partition_by customer_id)

**Kiểm tra:** `check.py S5`.

**Câu hỏi suy ngẫm**
1. Vì sao đổi `null` thành `9999-12-31`?
2. Vì sao surrogate key phải gồm cả `dbt_valid_from`?

---

## S6 ⭐⭐⭐⭐ Point-in-time join

**Yêu cầu:** `fct_orders_pit` = mỗi đơn kèm **thuộc tính khách hàng tại thời điểm đặt đơn**:

| Cột | |
|---|---|
| `order_id`, `order_date`, `customer_id`, `order_status`, `amount` | từ `fct_orders` |
| `customer_sk` | phiên bản khách hợp lệ lúc đặt đơn; không tìm thấy → `'-1'` |
| `customer_city_at_order`, `customer_tier_at_order` | không tìm thấy → `'Unknown'` |

**Quy ước:** phiên bản hợp lệ khi `valid_from <= cast(order_date as timestamp) < valid_to` (tức lúc 00:00 ngày đặt đơn).

**Kiểm tra:** `check.py S6` ở các ngày 1, 2, 3, 5.

**Quan sát**
1. Đơn của khách 3 trải qua 3 thành phố. Đơn cũ vẫn giữ Ha Noi dù khách đã chuyển.
2. Đơn của khách 11 ở ngày 2 là `Unknown`; ngày 3 (khách 11 xuất hiện) tự được gán đúng. Vì sao? (gợi ý: `fct_orders_pit` là `table`)
3. Thử join "ngây thơ" theo `customer_id` với `is_current` → check sẽ FAIL và chỉ rõ đơn nào sai.

**Câu hỏi suy ngẫm**
1. Nếu `fct_orders_pit` là incremental, đơn đã gán `Unknown` sẽ ra sao khi khách đến sau? Thiết kế cách xử lý (thử ở bài thử thách cuối).
2. `customer_tier_at_order` của khách 5 sau ngày 3 có đúng không? Lỗi bắt nguồn từ đâu?

---

## S7 ⭐⭐⭐⭐ SCD2 tự viết bằng incremental

**Mục tiêu:** hiểu snapshot làm gì bên trong bằng cách tự dựng SCD2, **không** dùng snapshot.

**Yêu cầu:** `dim_customers_scd2_manual` từ `stg_customers`, chỉ theo dõi `city`, `tier`:

| Cột | |
|---|---|
| `scd_id` | hash(`customer_id`, `valid_from`) — `unique_key` |
| `customer_id`, `city`, `tier` | |
| `row_hash` | hash(`city`, `tier`) để so sánh thay đổi |
| `valid_from` | `_loaded_at` của phiên bản |
| `valid_to` | null nếu đang hiệu lực |
| `is_current` | |

Hành vi mỗi lần chạy:
- Khách mới → thêm phiên bản mở.
- `city`/`tier` đổi → đóng phiên bản cũ (`valid_to` = `_loaded_at` mới) + thêm phiên bản mới.
- Chỉ đổi email → **không** làm gì.
- Khách biến mất khỏi nguồn → đóng phiên bản đang mở.
- Chạy 2 lần trong cùng một ngày → không thay đổi gì (idempotent).

`materialized='incremental'`, `incremental_strategy='delete+insert'`, `unique_key='scd_id'`.

**Kiểm tra:** `./scripts/replay.sh` rồi `check.py S7`. Khách 5 phải có 2 phiên bản dù `updated_at` không đổi.

**Câu hỏi suy ngẫm**
1. Vì sao dùng `_loaded_at` cho `valid_from` thay vì `updated_at`?
2. Vì sao dòng bị đóng phải **giữ nguyên** `scd_id` cũ?
3. Phiên bản bị xoá đóng bằng thời gian nào? Có chính xác không?
4. So với snapshot: bạn vừa tự viết lại phần nào của snapshot?

<details><summary>Gợi ý cấu trúc CTE</summary>

```
source        -- stg_customers + row_hash
current_rows  -- {{ this }} where is_current                  (chỉ khi is_incremental)
changed       -- source left join current_rows: khách mới hoặc row_hash khác
deleted       -- current_rows không còn trong source
closed        -- current_rows thuộc changed hoặc deleted → valid_to, is_current = false
new_versions  -- từ changed
select new_versions union all closed
```
</details>

---

## S8 SCD2 từ CDC log

⭐⭐⭐⭐ — kèm bài J10.

**Bối cảnh:** `raw.customer_changelog` ghi **mọi** thay đổi kèm `changed_at` chính xác (op I/U/D). Có log này thì không cần snapshot: lịch sử dựng lại được bất cứ lúc nào.

**Yêu cầu**
1. **J10:** macro `scd2_from_changelog(relation, key, changed_at, tracked_columns, op_column='op', delete_value='D')` sinh SQL SCD2:
   - Chỉ tạo phiên bản mới khi `tracked_columns` thay đổi (khách 2 đổi email → **không** có phiên bản mới). Đây là bài toán *gaps and islands*.
   - `op = 'D'` → đóng phiên bản trước đó, không tạo phiên bản.
   - `valid_from` = `changed_at`; `valid_to` = `changed_at` của thay đổi kế tiếp; `is_current`; `scd_id`.
2. Model `dim_customers_from_cdc` = gọi macro với `stg_customer_changelog`, `tracked_columns=['city', 'tier']`, `materialized='table'`.

**Kiểm tra:** `check.py S8` (kiểm tra cả `valid_from` của khách 3 phải là đúng 10:00 ngày chuyển nhà).

**Thử nghiệm quan trọng**
```bash
python scripts/simulate.py goto 5        # nhảy thẳng, KHÔNG build các ngày ở giữa
dbt build --exclude fct_events_microbatch
python scripts/check.py S1 S7 S8
```
S1 và S7 FAIL (thiếu lịch sử), S8 vẫn PASS. Đây là khác biệt cốt lõi giữa *chụp trạng thái* và *có log thay đổi*.

**Câu hỏi suy ngẫm**
1. Trong thực tế CDC log đến từ đâu? (Debezium, Fivetran history mode, binlog/WAL...)
2. Có CDC log rồi thì còn lý do gì để dùng snapshot?

<details><summary>Gợi ý</summary>

`lag(hash) over (partition by key order by changed_at)` để biết dòng trước; giữ dòng khi: là dòng đầu, dòng trước là D, hash khác dòng trước, hoặc chính nó là D. Sau đó `lead(changed_at)` để có `valid_to`, cuối cùng bỏ các dòng D.
</details>
