# Bước 3 — Mô hình hoá thelook (áp dụng tuần 4)

> Lý thuyết: [5.2 thelook](../../GD2-ly-thuyet/tuan-5/02-thelook-ecommerce.md), toàn bộ [tuần 4](../../GD2-ly-thuyet/README.md)

Đây là phần **của bạn**: không có đáp án, chỉ có đặc tả và tiêu chí. Làm theo đúng quy trình 4 bước: quy trình → grain → dimension → fact.

## 1. Staging (7 model)

| Model | Grain | Việc cần làm |
|---|---|---|
| `stg_thelook__users` | khách | đổi `id` → `customer_id`, chuẩn hoá chuỗi |
| `stg_thelook__orders` | đơn | (đã làm ở bước 2) |
| `stg_thelook__order_items` | món hàng | `id` → `order_item_id`, `sale_price` → `sale_amount` |
| `stg_thelook__products` | sản phẩm | `id` → `product_id` |
| `stg_thelook__inventory_items` | đơn vị hàng trong kho | `id` → `inventory_item_id`, `created_at` → `stocked_at` |
| `stg_thelook__distribution_centers` | trung tâm | |
| `stg_thelook__events` | sự kiện | `limit_in_dev`! Bảng lớn nhất |

Test: khoá chính `unique` + `not_null`; `accepted_values` cho `status`, `event_type` (lấy danh sách bằng `select distinct`); `relationships` giữa order_items và orders.

⚠️ Dữ liệu cập nhật liên tục → **đừng** viết test kiểu "đúng 100.000 dòng". Dữ liệu dev bị cắt 90 ngày → test `relationships` có thể đỏ ở dev (món của đơn cũ hơn 90 ngày). Cách xử lý: `config: where` giới hạn test, hoặc `severity: warn` ở dev:

```yaml
- relationships:
    arguments: {to: ref('stg_thelook__orders'), field: order_id}
    config:
      severity: "{{ 'warn' if target.name in ['dev', 'ci'] else 'error' }}"
```

## 2. Marts

| Model | Loại | Grain | Ghi chú |
|---|---|---|---|
| `dim_date` | dimension | ngày | `dbt_utils.date_spine` hoặc `GENERATE_DATE_ARRAY`; dòng `-1` |
| `dim_customer` | dimension (Type 1) | khách | tuổi → nhóm tuổi; `traffic_source` lúc đăng ký |
| `dim_product` | dimension (Type 1) | sản phẩm | `department`, `category`, `brand` (làm phẳng) |
| `dim_distribution_center` | dimension | trung tâm | |
| `fct_order_items` | transaction | món hàng | `sale_amount`, `cost` (từ inventory), `gross_margin`; khoá ngày đặt; trạng thái món |
| `fct_order_fulfillment` | accumulating snapshot | đơn **hoặc** món hàng (bạn chọn, ghi lý do) | mốc: tạo, gửi, giao, trả; `-1` cho mốc chưa tới; lag ngày |
| `fct_events` | transaction | sự kiện | incremental, partition theo ngày (tuần 7 tối ưu tiếp) |
| `fct_sessions` (tuỳ chọn) | transaction | phiên | từ `events`: số trang, có mua không, thời lượng |
| `fct_inventory_daily` (tuỳ chọn) | periodic snapshot | sản phẩm × trung tâm × ngày | tồn = đã nhập ≤ ngày đó và (chưa bán hoặc bán sau ngày đó) |

Yêu cầu chung:
- `description` của mọi fact ghi **grain** + **loại fact**.
- Test unique trên grain của mọi fact.
- `relationships` từ khoá fact tới dimension.
- `bus_matrix.yml` + bảng bus matrix trong README (giống K14 của lab).
- `fct_events`: incremental. Thử cả `merge` và `insert_overwrite`, giữ cái bạn chọn, ghi số byte xử lý của mỗi cách (chuẩn bị cho playbook tuần 7).

Gợi ý `fct_events` (BigQuery):

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by={'field': 'event_date', 'data_type': 'date'},
    cluster_by=['event_type', 'customer_id']
) }}

select
    event_id, session_id, customer_id, event_type, uri, traffic_source,
    event_created_at, date(event_created_at) as event_date
from {{ ref('stg_thelook__events') }}
{% if is_incremental() %}
where event_created_at >= timestamp(date_sub(_dbt_max_partition, interval 2 day))
{% endif %}
```

## 3. Tự kiểm tra

```bash
dbt build                                   # dev: xanh
dbt build -s fct_events                     # chạy lần 2: incremental, xem bytes_processed trong log
python -c "import json; r=json.load(open('target/run_results.json')); [print(x['unique_id'], x['adapter_response'].get('bytes_processed')) for x in r['results'] if 'adapter_response' in x]"
```

## ✅ Xong bước 3 khi

- [ ] 7 staging + ≥ 3 dimension + `fct_order_items` + `fct_order_fulfillment` + `fct_events` build xanh ở dev
- [ ] Mọi fact có grain trong description và test unique đúng grain
- [ ] `bus_matrix.yml` + bảng trong README
- [ ] Đã ghi số byte xử lý của `fct_events` lần đầu và lần incremental
