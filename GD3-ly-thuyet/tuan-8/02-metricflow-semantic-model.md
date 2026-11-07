# 8.2 MetricFlow: semantic model, entity, dimension, time spine

> Phiên bản tham chiếu: dbt-core 1.12.6 + dbt-metricflow 0.15 (metricflow 0.213). Mọi ví dụ đã chạy trên lab DuckDB.

## Hai kiểu YAML

dbt có 2 cú pháp khai báo semantic layer. Cả hai chạy song song được trong cùng project.

**Spec mới (từ 2025, dùng trong lab):** khai báo ngay trên model, entity và dimension gắn vào cột, metric simple khai báo thẳng `agg`/`expr`. Không còn `measures`.

```yaml
models:
  - name: fct_orders
    semantic_model:
      enabled: true
      name: orders                 # tên semantic model (mặc định = tên model)
    agg_time_dimension: order_date # cột thời gian mặc định cho metric của model này
    columns:
      - name: order_id
        entity: {type: primary, name: sales_order}
      - name: customer_id
        entity: {type: foreign, name: customer}
      - name: order_date
        granularity: day
        dimension: {type: time}
      - name: channel
        dimension: {type: categorical}
    metrics:
      - name: orders
        type: simple
        agg: count
        expr: order_id
        filter: "{{ Dimension('sales_order__is_cancelled') }} = false"
```

**Spec cũ (dbt 1.6–1.9, vẫn gặp nhiều ở công ty và trong tài liệu ôn thi):** khối `semantic_models:` riêng, có `measures:`, metric tham chiếu measure qua `type_params`.

```yaml
semantic_models:
  - name: orders
    model: ref('fct_orders')
    defaults: {agg_time_dimension: order_date}
    entities:
      - {name: sales_order, type: primary, expr: order_id}
      - {name: customer, type: foreign, expr: customer_id}
    dimensions:
      - {name: order_date, type: time, type_params: {time_granularity: day}}
      - {name: channel, type: categorical}
    measures:
      - {name: order_count, agg: count, expr: order_id}
metrics:
  - name: orders
    type: simple
    type_params: {measure: order_count}
```

> **Đã kiểm chứng trên dbt-core 1.12.6** (lab tuần 8–10):
> - Spec mới: `fill_nulls_with` của metric được chấp nhận nhưng **bị bỏ qua** (`semantic_manifest.json` ghi `null`). Spec cũ (`type_params.measure.fill_nulls_with`) chạy đúng.
> - Spec mới: khối `semantic_model:` trên model **có `versions:`** bị bỏ qua lặng lẽ. Spec cũ với `model: ref('dim_customers', v=2)` chạy đúng.
> - Sửa YAML semantic mà `dbt parse` báo trùng tên vô lý thì chạy `dbt parse --no-partial-parse`.
>
> Bài học: **luôn mở `target/semantic_manifest.json` kiểm tra** sau khi khai báo. Đó là thứ MetricFlow thật sự đọc.

## Entity: chìa khoá của mọi join

| Loại | Ý nghĩa | Ví dụ |
|---|---|---|
| `primary` | Mỗi dòng có đúng 1 giá trị, không NULL, không trùng | `order_id` trên `fct_orders` |
| `unique` | Không trùng nhưng có thể NULL | `email` trên bảng khách (nếu có) |
| `foreign` | Có thể trùng, có thể NULL | `customer_id` trên `fct_orders` |
| `natural` | Khoá tự nhiên của bảng SCD2, dùng với `validity_params` | `customer_code` trên `dim_customer_scd2` |

MetricFlow nối 2 semantic model khi chúng có **entity cùng tên**. Quy tắc join (rút gọn):

| Từ \ tới | primary / unique | foreign |
|---|---|---|
| **foreign** | ✅ many-to-one (an toàn) | ❌ many-to-many → fan-out |
| **primary / unique** | ✅ one-to-one | ❌ one-to-many → fan-out |

Vì vậy metric trên `fct_order_items` (có `sales_order` foreign) lấy được dimension của `fct_orders` (có `sales_order` primary). Ngược lại, metric trên `fct_orders` **không** lấy được `product__category`, vì một đơn có nhiều sản phẩm. Muốn "số đơn theo danh mục" thì định nghĩa metric `count_distinct(order_id)` trên `fct_order_items`, và chấp nhận một đơn có 2 danh mục được đếm ở cả hai.

**Multi-hop:** MetricFlow đi được nhiều bước (`order_item → sales_order → customer`). Tên dimension khi đó có cả đường đi, ví dụ `sales_order__customer__city`. Lab đặt sẵn `customer_id` lên `fct_order_items` (đúng kiểu Kimball: fact mang mọi khoá ngoại), nên `customer__city` chỉ cần 1 bước.

**Đặt tên entity:** dùng danh từ số ít, **tránh từ khoá SQL**. Entity tên `order` làm MetricFlow sinh `... AS order` và truy vấn gộp nhiều metric bị lỗi cú pháp (đã gặp trên DuckDB). `sales_order`, `customer`, `product` là tên an toàn.

## Dimension

```yaml
      - name: order_date
        granularity: day          # grain nhỏ nhất của cột
        dimension: {type: time}
      - name: is_cancelled
        dimension: {type: categorical}
```

- Tên đầy đủ khi truy vấn: `<entity>__<dimension>`, ví dụ `sales_order__channel`, `product__category`.
- **`metric_time`** là dimension thời gian đặc biệt: mỗi metric tự hiểu `metric_time` là `agg_time_dimension` của nó. `revenue` dùng `order_date`, `refunds` dùng `refund_date`, nhưng cả hai cùng group được theo `metric_time__day`.
- Grain khi truy vấn: `metric_time__day`, `__week`, `__month`, `__quarter`, `__year`.
- Dimension trên bảng SCD2: dùng `validity_params` (`is_start`, `is_end`) và entity `natural`. MetricFlow sẽ join "đúng phiên bản tại thời điểm giao dịch". Lab không có, nhưng `adventure_works` có snapshot thì thử được.

## Time spine

MetricFlow cần một bảng ngày liên tục để:

- tính **cumulative** (mỗi ngày nhìn lùi một cửa sổ),
- tính **offset** (`revenue` 7 ngày trước),
- lấp ngày không có dữ liệu (`join_to_timespine`).

```yaml
models:
  - name: metricflow_time_spine
    time_spine:
      standard_granularity_column: date_day
    columns:
      - name: date_day
        granularity: day
```

Phủ đủ rộng: từ ngày dữ liệu sớm nhất tới vài năm sau. Có thể khai báo thêm spine theo giờ, hoặc **custom granularity** (`fiscal_quarter`, tuần bán lẻ 4-4-5) bằng các cột phụ của spine.

## Kiểm tra trong lúc làm

```bash
dbt parse                                   # sinh target/semantic_manifest.json
mf validate-configs --skip-dw               # kiểm tra ngữ nghĩa (không chạm warehouse)
mf validate-configs                         # + chạy thử trên warehouse
mf list metrics                             # metric + dimension dùng được với nó
mf list dimensions --metrics revenue
mf query --metrics revenue --group-by metric_time__day --start-time 2026-11-01 --end-time 2026-11-07 --explain
```

## Câu hỏi tự kiểm tra

1. Vì sao `fct_orders` không lấy được `product__category`? Viết metric "số đơn có ít nhất 1 sản phẩm Điện tử".
2. `metric_time` của `revenue` và `refunds` là 2 cột khác nhau. Khi group theo `metric_time__month`, ý nghĩa nghiệp vụ của `refund_rate` là gì?
3. Một bảng `dim_customer` SCD2 cần khai báo gì để `revenue` theo `customer__city` lấy đúng thành phố **tại thời điểm mua**?
4. Bạn sẽ đưa lệnh nào vào CI để bắt lỗi semantic layer trước khi merge?

## Tài liệu

- dbt docs: *Semantic models*, *Entities*, *Dimensions*, *MetricFlow time spine*, *Join logic*
- dbt docs: *Semantic Layer YAML spec* (trang so sánh spec mới và cũ)
- Release notes của dbt-core và `dbt-labs/metricflow` trên GitHub: theo dõi khi nào 2 lỗi đã ghi ở trên được sửa (chạy lại lab để xác nhận)
