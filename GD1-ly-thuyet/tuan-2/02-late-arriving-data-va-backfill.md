# 2.2 Late-arriving data và backfill

## Late-arriving data là gì

Dữ liệu **đến kho muộn hơn thời điểm sự kiện xảy ra**. Ví dụ: đơn hàng ngày 10 nhưng hệ thống nguồn sync trễ, ngày 13 mới vào bảng raw.

Với filter incremental kiểu watermark đơn giản:

```sql
where order_date > (select max(order_date) from {{ this }})
```

Nếu ngày 12 đã được load, đơn ngày 10 đến muộn sẽ **bị bỏ qua mãi mãi** → số liệu thiếu mà không ai biết.

```
Thời gian sự kiện:   10    11    12    13
Lần chạy ngày 12:   [██]  [██]  [██]          max = 12
Đơn ngày 10 đến muộn vào ngày 13 ──┐
Lần chạy ngày 13: where order_date > 12  ──▶  đơn ngày 10 bị loại ❌
```

## Phân biệt 2 loại thời gian

| | Ý nghĩa | Ví dụ cột |
|---|---|---|
| **Event time** | Lúc sự kiện xảy ra | `order_date` |
| **Load/processing time** | Lúc dữ liệu vào kho / bị sửa | `_loaded_at`, `modified_at` |

Cách xử lý đơn giản nhất: **lọc incremental theo load time** thay vì event time — đơn ngày 10 vào lúc ngày 13 có `_loaded_at` = 13 nên vẫn được lấy. Nhưng không phải nguồn nào cũng có cột load time tin cậy.

## Giải pháp 1: Lookback window

Lùi watermark lại N ngày, kết hợp `merge`/`delete+insert` để không bị trùng:

```sql
{{ config(materialized='incremental', unique_key='sales_key', incremental_strategy='merge') }}

select ...
from {{ ref('int_orders__joined_details') }}

{% if is_incremental() %}
where modified_at >= (
    select {{ dbt.dateadd('day', -var('lookback_days', 3), 'max(modified_at)') }}
    from {{ this }}
)
{% endif %}
```

- Đánh đổi: N lớn → an toàn hơn nhưng xử lý nhiều hơn.
- Chọn N dựa trên **dữ liệu thật**: đo độ trễ `_loaded_at - order_date`, lấy p99 rồi cộng biên.
- **Bắt buộc** đi với chiến lược idempotent (merge/delete+insert). Lookback + `append` = dữ liệu trùng.
- Nên đóng gói thành macro `get_incremental_filter(column, lookback_days)` (gợi ý ở 1.3).

## Giải pháp 2: Microbatch (dbt ≥ 1.9)

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='order_date',
    batch_size='day',
    lookback=3,
    begin='2011-05-01'
) }}
select * from {{ ref('int_orders__joined_details') }}
```

- Không cần viết `is_incremental()`; dbt tự lọc theo `event_time` cho từng batch.
- `lookback=3` → mỗi lần chạy xử lý lại 3 batch trước đó.
- Model upstream cũng khai báo `event_time` thì dbt lọc được cả input.
- Batch lỗi có thể `dbt retry` riêng batch đó.

## Late-arriving dimension (early-arriving fact)

Trường hợp ngược: **fact đến trước dimension**. Đơn hàng có `customer_id = 999` nhưng `dim_customers` chưa có khách 999.

- Inner join → mất dòng fact.
- Cách Kimball: left join + gán **khoá "unknown member"** (vd `-1` hoặc hash của `'unknown'`), dimension có sẵn 1 dòng "Unknown". Khi dimension đến sau, lần build kế tiếp (lookback) sẽ cập nhật lại khoá đúng.

```sql
coalesce(dim_customers.customer_key, '{{ var("unknown_key", "-1") }}') as customer_key
```

Chủ đề này học sâu ở tuần 4 (Kimball). Tuần 2 chỉ cần hiểu và có 1 ví dụ.

---

## Backfill là gì

Nạp lại/tính lại dữ liệu cho **một khoảng thời gian trong quá khứ**. Lý do:
- Sửa bug logic → phải tính lại số cũ.
- Thêm cột mới → cần giá trị cho lịch sử.
- Nguồn nạp bổ sung dữ liệu cũ.

## Các cách backfill trong dbt

| Cách | Lệnh | Khi nào |
|---|---|---|
| Full refresh | `dbt build -s fct_sales --full-refresh` | Bảng còn vừa phải, muốn chắc chắn đúng tuyệt đối |
| Theo khoảng ngày bằng vars | `dbt run -s fct_sales --vars '{"start_date": "2013-01-01", "end_date": "2013-12-31"}'` | Bảng lớn, chỉ sửa 1 khoảng |
| Microbatch | `dbt run -s fct_sales --event-time-start "2013-01-01" --event-time-end "2014-01-01"` | Model dùng microbatch |

Ví dụ backfill bằng vars:

```sql
{% if is_incremental() %}
  {% if var('start_date', none) is not none %}
    where order_date between '{{ var("start_date") }}' and '{{ var("end_date") }}'
  {% else %}
    where modified_at >= ... -- filter lookback bình thường
  {% endif %}
{% endif %}
```

### Bảo vệ bảng lớn khỏi full refresh nhầm

```sql
{{ config(full_refresh=false) }}
```

Khi đặt `false`, lệnh `--full-refresh` bị bỏ qua cho model này. Muốn rebuild phải chủ động đổi config — tránh lỡ tay xoá bảng lịch sử nhiều tỉ dòng.

## Lỗi hay gặp

- Watermark theo event time, không có lookback → mất dữ liệu trễ im lặng.
- Lookback với `append` → trùng dữ liệu.
- Backfill bằng vars nhưng chiến lược `merge` không có `unique_key` → trùng.
- Không đo độ trễ thật, chọn N theo cảm tính.

## Áp dụng vào adventure_works

- [ ] Giả lập dữ liệu trễ: insert vài dòng `SalesOrderHeader` có `OrderDate` cũ nhưng `ModifiedDate` mới
- [ ] Chứng minh filter không lookback **bỏ sót** dòng đó, có lookback thì **lấy được**
- [ ] Macro `get_incremental_filter` dùng chung
- [ ] 1 ví dụ unknown member cho `dim_customers`
- [ ] Viết mục "Backfill runbook" trong README: lệnh cho từng tình huống

## Câu hỏi tự kiểm tra

1. Vì sao lọc theo event time dễ mất dữ liệu trễ?
2. Vì sao lookback bắt buộc phải đi với merge/delete+insert?
3. Chọn số ngày lookback dựa trên gì?
4. `full_refresh=false` dùng để làm gì?
5. Fact đến trước dimension thì xử lý thế nào để không mất dòng?

## Tài liệu

- https://docs.getdbt.com/docs/build/incremental-models (mục "late-arriving")
- https://docs.getdbt.com/docs/build/incremental-microbatch
- https://docs.getdbt.com/reference/resource-configs/full_refresh
- Kimball, *The Data Warehouse Toolkit* — chương về late arriving facts/dimensions
