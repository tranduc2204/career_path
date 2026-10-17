# 2.3 Snapshots — SCD Type 2 (timestamp vs check)

## Bài toán

Bảng nguồn thường **ghi đè** giá trị cũ. Khách hàng chuyển từ territory "Northwest" sang "Southwest" → nguồn chỉ còn "Southwest". Báo cáo doanh thu năm ngoái theo territory sẽ bị **sai lịch sử**.

**Slowly Changing Dimension (SCD)** là các cách lưu thay đổi của dimension:

| Loại | Cách làm | Giữ lịch sử |
|---|---|---|
| Type 0 | Không bao giờ đổi | — |
| Type 1 | Ghi đè | ❌ |
| **Type 2** | Thêm dòng mới, đóng dòng cũ bằng khoảng hiệu lực | ✅ đầy đủ |
| Type 3 | Thêm cột "giá trị trước đó" | Chỉ 1 bước |

dbt **snapshot** = cách dựng SCD Type 2 tự động.

## Kết quả của snapshot

| customer_id | territory | dbt_valid_from | dbt_valid_to | dbt_scd_id | dbt_updated_at |
|---|---|---|---|---|---|
| 29825 | Northwest | 2012-01-01 | 2013-06-15 | a1b2... | 2012-01-01 |
| 29825 | Southwest | 2013-06-15 | `null` | c3d4... | 2013-06-15 |

- `dbt_valid_to = null` → bản ghi **hiện hành** (có thể đổi thành 1 ngày xa như `9999-12-31` bằng `dbt_valid_to_current`, dbt ≥ 1.9).
- `dbt_scd_id`: khoá duy nhất của từng phiên bản.

Lấy trạng thái tại một thời điểm:

```sql
where '2013-01-01' >= dbt_valid_from
  and '2013-01-01' <  coalesce(dbt_valid_to, '9999-12-31')
```

## Hai chiến lược phát hiện thay đổi

### `timestamp` (ưu tiên)

Dựa vào cột `updated_at` của nguồn: nếu `updated_at` mới hơn bản đã lưu → có thay đổi.

- ✅ Nhanh, chỉ so 1 cột.
- ❌ Cần nguồn có `updated_at` **đáng tin** (mọi update đều cập nhật cột này).

### `check`

So sánh giá trị các cột chỉ định (`check_cols`), khác → có thay đổi.

- ✅ Dùng được khi nguồn không có `updated_at` tin cậy.
- ❌ Chậm hơn (so nhiều cột); `check_cols='all'` rất tốn trên bảng rộng.
- ✅ Hữu ích khi chỉ quan tâm vài cột: các cột khác đổi thì **không** sinh phiên bản mới.

| | timestamp | check |
|---|---|---|
| Cần | `updated_at` | `check_cols` |
| Tốc độ | Nhanh | Chậm hơn |
| Bắt thay đổi | Mọi lần `updated_at` đổi | Chỉ khi cột chỉ định đổi |

## Cú pháp

### dbt ≥ 1.9: khai báo bằng YAML

```yaml
# snapshots/snap_customers.yml
snapshots:
  - name: snap_customers
    relation: ref('stg_sales__customers')
    config:
      schema: snapshots
      unique_key: customer_id
      strategy: timestamp
      updated_at: modified_at
      dbt_valid_to_current: "to_date('9999-12-31')"   # tuỳ warehouse
      hard_deletes: invalidate                         # ignore | invalidate | new_record

  - name: snap_products
    relation: ref('stg_production__products')
    config:
      schema: snapshots
      unique_key: product_id
      strategy: check
      check_cols: [list_price, standard_cost, product_subcategory_id]
```

### Cú pháp cũ (block SQL, vẫn gặp nhiều trong tài liệu)

```sql
-- snapshots/snap_customers.sql
{% snapshot snap_customers %}
{{ config(
    target_schema='snapshots',
    unique_key='customer_id',
    strategy='timestamp',
    updated_at='modified_at',
    invalidate_hard_deletes=True
) }}
select * from {{ source('sales', 'customer') }}
{% endsnapshot %}
```

Chạy: `dbt snapshot` (hoặc nằm trong `dbt build`).

## Hard deletes

Nếu dòng bị **xoá** ở nguồn, mặc định snapshot không biết (dòng cũ vẫn "hiện hành").
- `hard_deletes: invalidate` (cũ: `invalidate_hard_deletes=True`) → đóng `dbt_valid_to` của dòng đã xoá.
- `hard_deletes: new_record` → thêm 1 dòng đánh dấu `dbt_is_deleted = true`.

## Nguyên tắc dùng snapshot

1. **Snapshot gần nguồn nhất có thể** (source hoặc staging rất mỏng). Logic phức tạp đặt sau snapshot, vì snapshot **không rebuild lại được** lịch sử đã mất.
2. Snapshot là dữ liệu **không thể tái tạo** → schema riêng, không bao giờ drop, cần backup.
3. Chạy đều đặn (theo lịch). Thay đổi xảy ra giữa 2 lần chạy rồi lại đổi về sẽ **không được ghi nhận**.
4. Tạo `dim_` từ snapshot: thêm surrogate key = hash(`customer_id`, `dbt_valid_from`), join fact theo khoảng hiệu lực.

## Lỗi hay gặp

- Snapshot sau khi đã join/transform nhiều → đổi logic là hỏng lịch sử.
- `unique_key` không duy nhất → bản ghi nhân bản.
- `timestamp` với `updated_at` không đáng tin → bỏ sót thay đổi.
- Dùng `check_cols='all'` cho bảng 100 cột.
- Join fact với snapshot bằng `customer_id` thường (không theo khoảng thời gian) → nhân dòng.

## Áp dụng vào adventure_works

- [ ] `snap_customers` (timestamp, `ModifiedDate`)
- [ ] `snap_products` (check trên `ListPrice`, `StandardCost`)
- [ ] Giả lập thay đổi: update giá 1 sản phẩm → chạy `dbt snapshot` → thấy 2 phiên bản
- [ ] Giả lập xoá 1 dòng → kiểm tra hard delete
- [ ] `dim_products` SCD2 từ snapshot; `fct_sales` join theo `order_date` trong khoảng hiệu lực
- [ ] Test: tại mỗi `product_id` chỉ có đúng 1 dòng `dbt_valid_to is null`

## Câu hỏi tự kiểm tra

1. SCD Type 1 và Type 2 khác nhau thế nào? Ví dụ khi nào chọn Type 1?
2. Khi nào dùng `check` thay vì `timestamp`?
3. Vì sao nên snapshot ở gần nguồn?
4. Snapshot xử lý bản ghi bị xoá ở nguồn ra sao?
5. Viết câu SQL lấy giá sản phẩm tại ngày 2013-01-01.

## Tài liệu

- https://docs.getdbt.com/docs/build/snapshots
- https://docs.getdbt.com/reference/snapshot-configs
- Kimball, *The Data Warehouse Toolkit* — chương 5 (SCD)
