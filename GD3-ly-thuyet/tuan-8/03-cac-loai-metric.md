# 8.3 Các loại metric: simple, ratio, derived, cumulative, conversion

> Ví dụ dùng YAML spec mới (đã chạy trên lab). Spec cũ đặt các tham số trong `type_params:`.

## Bản đồ

| Loại | Công thức | Dùng khi | Ví dụ lab |
|---|---|---|---|
| **simple** | `agg(expr)` trên 1 semantic model | Tổng, đếm, distinct, min/max, percentile | `revenue`, `orders`, `buyers` |
| **ratio** | `metric_a / metric_b` | Tỉ lệ, trung bình có trọng số | `aov`, `conversion_rate`, `roas` |
| **derived** | biểu thức SQL trên các metric | Hiệu, tổng có điều kiện, so với kỳ trước | `gross_profit`, `net_revenue`, `revenue_wow` |
| **cumulative** | metric trong cửa sổ trượt / từ đầu kỳ | Luỹ kế, rolling distinct | `revenue_mtd`, `buyers_7d` |
| **conversion** | tỉ lệ entity làm sự kiện A rồi B trong cửa sổ | Phễu | phiên → đơn trong 1 ngày |

## Simple

```yaml
    metrics:
      - name: revenue
        type: simple
        agg: sum                  # sum, count, count_distinct, average, min, max, median, percentile, sum_boolean
        expr: line_amount         # cột hoặc biểu thức SQL
        filter: "{{ Dimension('sales_order__is_cancelled') }} = false"
      - name: cogs
        type: simple
        agg: sum
        expr: line_cost
        hidden: true              # không lộ ra cho người dùng, chỉ làm input
```

- **`filter` trong định nghĩa metric** là cách "khoá" nghiệp vụ: không ai quên lọc đơn huỷ. Filter dùng được dimension của semantic model khác (MetricFlow tự join).
- Cú pháp filter: `{{ Dimension('entity__dim') }}`, `{{ TimeDimension('metric_time', 'day') }}`, `{{ Entity('customer') }}`, `{{ Metric('orders', group_by=['customer']) }} > 1` (lọc theo metric, ví dụ "khách mua ≥ 2 đơn").
- `count` trên khoá chính tương đương đếm dòng. `count_distinct` không cộng dồn được qua grain, và MetricFlow biết điều đó.
- **Non-additive** (`non_additive_dimension`): cho số dư kiểu semi-additive (tồn kho, số dư tài khoản): "lấy giá trị ngày cuối kỳ, không cộng". Đã gặp ở GĐ2 (periodic snapshot).

## Ratio

```yaml
  - name: aov
    type: ratio
    numerator: revenue
    denominator: orders
```

Ratio tính tử và mẫu **ở grain được hỏi** rồi mới chia. Vì thế AOV tháng = Σrevenue tháng / Σorders tháng, luôn đúng. Trung bình cộng các AOV ngày là **sai**: ngày ít đơn có trọng số bằng ngày nhiều đơn. Tử và mẫu có thể đến từ 2 semantic model khác nhau (`conversion_rate` = orders / sessions).

Có thể đặt filter riêng cho tử hoặc mẫu:

```yaml
    numerator:
      name: orders
      filter: "{{ Dimension('sales_order__channel') }} = 'app'"
      alias: app_orders
    denominator: orders
```

## Derived

```yaml
  - name: revenue_wow
    type: derived
    expr: (revenue - revenue_7d_ago) / revenue_7d_ago
    input_metrics:
      - name: revenue
      - name: revenue
        offset_window: 7 days       # giá trị của 7 ngày trước
        alias: revenue_7d_ago
```

- `offset_window: 1 month` → cùng ngày tháng trước. `offset_to_grain: month` → giá trị từ đầu tháng (dùng cho "so với đầu kỳ").
- **NULL lan truyền.** Ngày không có hoàn tiền thì `refunds` không có dòng, nên `revenue - refunds` = NULL. Cách chuẩn là `fill_nulls_with: 0` + `join_to_timespine: true` trên metric input. Trên dbt-core 1.12.6 với spec mới, `fill_nulls_with` bị bỏ qua khi parse (8.2), nên lab dùng `revenue - coalesce(refunds, 0)` ngay trong `expr`.
- Chia cho 0: `revenue_wow` khi tuần trước = 0 ra NULL. Kiểm tra cách warehouse của bạn xử lý chia cho 0.

## Cumulative

```yaml
  - name: revenue_mtd
    type: cumulative
    input_metric: revenue
    grain_to_date: month        # luỹ kế từ đầu tháng
    period_agg: last            # khi gom lên grain lớn hơn ngày: lấy ngày cuối kỳ
  - name: buyers_7d
    type: cumulative
    input_metric: buyers
    window: 7 days              # cửa sổ trượt [d-6, d]
    period_agg: last
```

- Không có `window` lẫn `grain_to_date` nghĩa là luỹ kế từ đầu dữ liệu (*all-time*).
- Trên metric `count_distinct`, cumulative đếm **distinct trong cửa sổ**: một khách mua 3 ngày trong tuần vẫn chỉ là 1. Cộng `buyers` 7 ngày thì đếm 3.
- **`period_agg`** (`first` mặc định, `last`, `average`) quyết định giá trị khi bạn hỏi cumulative ở grain lớn hơn grain gốc. Hỏi `revenue_mtd` theo `metric_time__month` với mặc định `first` thì ra **doanh thu ngày 1 của tháng**, không phải doanh thu cả tháng. Lab chấm đúng chỗ này.
- Cumulative cần **time spine**.

## Conversion

```yaml
  - name: session_to_order_rate
    type: conversion
    entity: customer              # đi theo khách
    calculation: conversion_rate  # hoặc conversions (đếm)
    base_metric: sessions
    conversion_metric: orders
    window: 1 day
```

MetricFlow lấy mỗi sự kiện base (phiên của khách X), tìm sự kiện conversion (đơn của khách X) xảy ra **sau** nó trong `window`. Kinh nghiệm từ lab: phép so sánh dùng `metric_time` đã cắt theo grain truy vấn. Với grain ngày và `window: 1 day`, "trong 1 ngày" thực tế là **cùng ngày**. Đọc `--explain` trước khi tin con số. Phiên không có `customer_id` (khách chưa đăng nhập) không bao giờ chuyển đổi được, nên lỗi tracking ngày 03/12 làm metric này sụt dù đơn hàng không đổi.

## Saved query và export

```yaml
saved_queries:
  - name: daily_kpis
    query_params:
      metrics: [revenue, orders, aov, net_revenue]
      group_by: ["TimeDimension('metric_time', 'day')"]
      where: ["{{ Dimension('sales_order__channel') }} = 'web'"]   # tuỳ chọn
    exports:
      - name: daily_kpis
        config: {export_as: table, schema: semantic}
```

- `mf query --saved-query daily_kpis` (Core). Trên dbt platform, saved query còn dùng làm cache và `exports` ghi kết quả thành bảng sau mỗi job.
- Saved query là "hợp đồng" giữa đội dữ liệu và một dashboard cụ thể. Gắn exposure vào metric (bài G6) để thấy lineage.

## Bảng tra nhanh: lỗi hay gặp

| Triệu chứng | Nguyên nhân |
|---|---|
| Doanh thu cao hơn Finance vài % | quên filter đơn huỷ / gồm phí ship |
| AOV tháng lệch | dùng `average` trên bảng đã tổng hợp theo ngày, không dùng ratio |
| "Khách tuần này" quá cao | cộng distinct theo ngày thay vì cumulative window |
| MTD theo tháng = số ngày 1 | `period_agg` mặc định `first` |
| Ngày trống ra NULL ở derived | thiếu `fill_nulls_with` / `coalesce` |
| `mf query` lỗi cú pháp khi gộp metric | entity trùng từ khoá SQL |
| `Could not find dimension` | sai tên `entity__dim`, hoặc đường join cần fan-out nên bị chặn |

## Câu hỏi tự kiểm tra

1. Viết `active_customers_30d` và `new_customer_revenue` (doanh thu từ khách có `signup_date` trong cùng tháng). Loại nào?
2. Vì sao `buyers_7d` gom lên tháng với `period_agg: average` có thể hữu ích hơn `last`?
3. Metric "tỉ lệ đơn app" nên là ratio có filter ở tử, hay derived từ 2 simple metric? Khác nhau gì?
4. Conversion metric khác `orders / sessions` ở điểm nào?

## Tài liệu

- dbt docs: *Simple / Ratio / Derived / Cumulative / Conversion metrics*, *Metrics as filters*, *Saved queries*, *Fill null values for metrics*
