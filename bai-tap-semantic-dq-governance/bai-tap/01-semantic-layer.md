# 01 — Semantic layer với MetricFlow (M1–M8)

> Lý thuyết: [GD3-ly-thuyet/tuan-8](../../GD3-ly-thuyet/README.md#tuần-8-312--912--semantic-layer). Chấm: `python scripts/check.py M`.
> Không cần đi qua các ngày: làm ở ngày 0 là đủ. `check.py` so kết quả `mf query` với SQL viết thẳng trên các bảng mart.

Bạn viết **YAML theo spec mới** (khối `semantic_model:` gắn vào model, metric khai báo bằng `agg:`), là spec dbt dùng từ 2025. Spec cũ (`semantic_models:` + `measures:`) vẫn chạy được, và bạn sẽ cần nó ở bài G4.

Đặt khai báo semantic **ngay trong file YAML của model** (`models/marts/commerce/_commerce.yml`...): một model chỉ được khai báo ở một chỗ. Metric dùng input từ nhiều model đặt ở khoá `metrics:` cấp cao nhất, ví dụ trong `models/semantic/_metrics.yml`.

## Tên bắt buộc (check.py truy vấn đúng các tên này)

| Model | `semantic_model.name` | Entity primary | Entity foreign | Dimension | Thời gian tổng hợp |
|---|---|---|---|---|---|
| `fct_orders` | `orders` | `sales_order` (order_id) | `customer`, `marketing_channel` (utm_source) | `channel`, `payment_method`, `status`, `is_cancelled` | `order_date` |
| `fct_order_items` | `order_items` | `order_item` | `sales_order`, `product`, `customer`, `marketing_channel` | | `order_date` |
| `fct_refunds` | `refunds` | `refund` | `sales_order` | `reason` | `refund_date` |
| `dim_products` | `products` | `product` | | `category`, `brand` | |
| `dim_customers` | `customers` | `customer` | | `city`, `segment` | |
| `fct_sessions` | `sessions` | `session` | `customer`, `marketing_channel` | `device` | `session_date` |
| `fct_ad_spend` | `ad_spend` | `ad_spend_row` (ad_spend_id) | `marketing_channel` | | `spend_date` |
| `dim_marketing_channels` | `marketing_channels` | `marketing_channel` (utm_source) | | `channel_name`, `channel_group` | |

15 metric được chấm:

| Loại | Metric |
|---|---|
| simple | `revenue`, `orders`, `buyers`, `refunds`, `sessions`, `ad_spend` (+ `cogs` ẩn, làm input) |
| ratio | `aov` = revenue / orders, `refund_rate` = refunds / revenue, `conversion_rate` = orders / sessions, `roas` = revenue / ad_spend |
| derived | `gross_profit` = revenue − cogs, `net_revenue` = revenue − refunds, `revenue_wow` = (revenue − revenue 7 ngày trước) / revenue 7 ngày trước |
| cumulative | `revenue_mtd` (luỹ kế từ đầu tháng), `buyers_7d` (khách distinct trong 7 ngày [d−6, d]) |

---

## M1 ⭐ — Time spine

Tạo `models/semantic/metricflow_time_spine.sql`: 1 dòng / ngày, phủ **ít nhất 2026-01-01 → 2027-12-31**, cột `date_day`. Khai báo:

```yaml
models:
  - name: metricflow_time_spine
    time_spine:
      standard_granularity_column: date_day
    columns:
      - name: date_day
        granularity: day
```

`dbt_project.yml` đã bật cờ `require_yaml_configuration_for_mf_time_spines`. Kiểm tra: `dbt build -s metricflow_time_spine && mf validate-configs --skip-dw`.

<details><summary>Gợi ý</summary>

DuckDB: `select cast(range as date) as date_day from range(date '2025-01-01', date '2028-01-01', interval 1 day)`.
</details>

## M2 ⭐⭐ — Semantic model, entity, dimension

Khai báo 8 semantic model theo bảng trên. Mỗi cột là entity hoặc dimension thì thêm `entity:` / `dimension:` vào cột đó:

```yaml
  - name: fct_orders
    semantic_model:
      enabled: true
      name: orders
    agg_time_dimension: order_date
    columns:
      - name: order_id
        entity: {type: primary, name: sales_order}
      - name: order_date
        granularity: day
        dimension: {type: time}
      - name: channel
        dimension: {type: categorical}
```

Một cột có thể vừa là entity vừa là dimension. Sau khi khai báo, chạy `mf list dimensions --metrics <metric>` để xem MetricFlow nối được tới đâu.

**Câu hỏi:** vì sao bảng yêu cầu đặt tên `sales_order` chứ không phải `order`? Thử đặt `order`, rồi chạy một truy vấn gộp kiểu `mf query --metrics revenue,revenue_mtd --group-by metric_time__day` (sau M6). Đọc SQL bằng `--explain`.

## M3 ⭐⭐ — Simple metric

6 metric simple + `cogs` (`hidden: true`). Theo định nghĩa nghiệp vụ trong [00-setup](00-setup.md#model-dựng-sẵn):

- `revenue`, `cogs` nằm trên `fct_order_items`, nhưng **trạng thái đơn lại nằm ở `fct_orders`**. Lọc bằng filter đi qua entity: `filter: "{{ Dimension('sales_order__is_cancelled') }} = false"`.
- `refunds` tính theo ngày hoàn tiền: đây là lý do mỗi semantic model có `agg_time_dimension` riêng. Khi truy vấn `metric_time`, MetricFlow tự dùng đúng cột thời gian của từng metric.

```bash
mf query --metrics revenue,orders,buyers --group-by metric_time__day --start-time 2026-11-24 --end-time 2026-11-30
mf query --metrics revenue --group-by metric_time__day --explain     # xem SQL sinh ra
```

## M4 ⭐⭐⭐ — Ratio

`aov`, `refund_rate`, `conversion_rate`, `roas`, đều là `type: ratio` với `numerator` / `denominator`.

`check.py` còn chấm **AOV theo tháng**. Nó phải bằng *tổng revenue tháng / tổng orders tháng*. Trung bình cộng của 30 AOV theo ngày thì sai. Ratio metric làm đúng việc này tự động. Giải thích được vì sao là bạn đã hiểu giá trị của semantic layer.

`conversion_rate` và `roas` lấy tử và mẫu từ **2 semantic model khác nhau**. MetricFlow tính riêng từng phía rồi nối theo `metric_time` (và theo dimension nếu có), không bao giờ join 2 bảng fact với nhau, nên không bị fan-out.

## M5 ⭐⭐⭐ — Derived

```yaml
metrics:
  - name: revenue_wow
    type: derived
    expr: (revenue - revenue_7d_ago) / revenue_7d_ago
    input_metrics:
      - name: revenue
      - name: revenue
        offset_window: 7 days
        alias: revenue_7d_ago
```

**Bẫy NULL:** có ngày không có hoàn tiền nào. Hôm đó `refunds` không có dòng, nên `revenue - refunds` = `revenue - NULL` = **NULL**. Doanh thu thuần của ngày đẹp nhất lại trống trơn. Cách "sách giáo khoa" là `fill_nulls_with: 0` (+ `join_to_timespine: true`) trên metric `refunds`.

> ⚠️ **Đã kiểm chứng trên dbt-core 1.12.6:** với YAML spec mới, `fill_nulls_with` của metric được chấp nhận nhưng **bị bỏ qua khi parse**. Mở `target/semantic_manifest.json`, tìm metric `refunds`: `"fill_nulls_with": null`. Spec cũ (`type_params: {measure: {name: ..., fill_nulls_with: 0}}`) thì chạy đúng. Hãy tự tìm cách cho `net_revenue` ra đúng mà vẫn dùng spec mới. `check.py` chấp nhận `refunds`/`refund_rate` = NULL vào ngày không có hoàn tiền, nhưng **`net_revenue` phải bằng `revenue`**.

<details><summary>Gợi ý</summary>

`expr` của derived metric là SQL chạy trên kết quả đã tổng hợp: `revenue - coalesce(refunds, 0)`.
</details>

## M6 ⭐⭐⭐⭐ — Cumulative

```yaml
  - name: revenue_mtd
    type: cumulative
    input_metric: revenue
    grain_to_date: month
  - name: buyers_7d
    type: cumulative
    input_metric: buyers
    window: 7 days
```

Chạy thử 2 truy vấn và so với số bạn tự tính bằng SQL:

```bash
mf query --metrics revenue_mtd --group-by metric_time__day   --start-time 2026-11-01 --end-time 2026-11-30
mf query --metrics revenue_mtd,revenue --group-by metric_time__month --start-time 2026-10-01 --end-time 2026-11-30
```

1. Truy vấn theo tháng ra `revenue_mtd` của tháng 11 là bao nhiêu, so với `revenue` cả tháng? Tại sao? (đọc về `period_agg`)
2. `buyers_7d` ngày 30/11 có bằng tổng `buyers` 7 ngày 24–30/11 không? Cái nào đúng với câu hỏi "tuần qua có bao nhiêu khách mua"?

`check.py` chấm `revenue_mtd` theo **cả ngày lẫn tháng**: MTD của một tháng = doanh thu cả tháng.

## M7 ⭐⭐⭐ — Truy vấn theo dimension

`check.py` chạy:

```bash
mf query --metrics revenue,aov --group-by sales_order__channel
mf query --metrics revenue --group-by product__category
mf query --metrics buyers --group-by customer__city
mf query --metrics sessions --group-by session__device
mf query --metrics revenue,ad_spend,roas --group-by marketing_channel__channel_group
```

Câu cuối là **conformed dimension** của Kimball phiên bản semantic layer: 3 fact (`order_items`, `ad_spend`, `sessions`) cùng nối được tới `marketing_channels` qua entity `marketing_channel`, nên ROAS theo nhóm kênh ra trong một câu. Với `organic` và `owned`, `ad_spend` là NULL nên `roas` cũng là NULL. Như vậy là đúng.

Đọc `--explain` của câu `customer__city`: MetricFlow join `fct_orders` → `dim_customers` theo kiểu nào (LEFT/INNER)? Khách có đơn nhưng không có trong CRM sẽ rơi vào đâu?

## M8 ⭐⭐ — Saved query

Tạo saved query `daily_kpis`: metric `revenue, orders, aov, net_revenue`, group theo `TimeDimension('metric_time', 'day')`. Thêm một `exports` dạng table.

```bash
mf query --saved-query daily_kpis --start-time 2026-11-24 --end-time 2026-11-30
```

`exports` chỉ chạy trên dbt platform (Cloud). Với Core, đây là "tài liệu sống" cho biết dashboard dùng những số nào. Ở bài G6 bạn sẽ nối dashboard với metric bằng exposure.

---

## Áp dụng vào project thật

- `thelook` (BigQuery): semantic model cho `fct_order_items`, `dim_users`, `dim_products` + 10 metric (gồm 1 ratio, 1 derived có offset, 1 cumulative). Ghi vào README những gì khác khi chạy trên BigQuery.
- `adventure_works` (Snowflake): metric doanh thu theo `SalesTerritory`, AOV, doanh thu luỹ kế năm (`grain_to_date: year`).

## Câu hỏi tự kiểm tra

1. Entity `primary`, `unique`, `foreign`, `natural` khác nhau thế nào? Join nào MetricFlow cho phép, join nào nó từ chối (fan-out)?
2. Vì sao ratio metric đúng ở mọi grain, còn "AOV tính sẵn trong bảng mart" thì không?
3. `offset_window` và `offset_to_grain` khác gì nhau? Viết metric "doanh thu cùng kỳ tháng trước".
4. Vì sao không nên đặt `filter` loại đơn huỷ trong câu truy vấn của dashboard, mà nên đặt trong định nghĩa metric?
