# 9.3 Elementary và anomaly detection

> Phiên bản tham chiếu: Elementary dbt package **0.26.1** (đã chạy trên DuckDB trong lab). CLI `edr` là gói Python riêng (`elementary-data`).

## Elementary gồm 2 phần

| Phần | Cài bằng | Làm gì |
|---|---|---|
| **dbt package** `elementary-data/elementary` | `packages.yml` | Test anomaly/schema dạng generic test; on-run-end hook ghi kết quả mọi lần chạy (`dbt_run_results`, `elementary_test_results`, `dbt_source_freshness_results`...) vào schema riêng |
| **CLI** `edr` | `pip install 'elementary-data[snowflake]'` (hoặc `[bigquery]`...) | `edr report` (báo cáo HTML: test, lineage, lịch sử), `edr monitor` (gửi cảnh báo Slack/Teams) |

```yaml
# dbt_project.yml
models:
  elementary:
    +schema: elementary
```

```bash
dbt deps && dbt run -s elementary      # tạo bảng hệ thống lần đầu
```

## Các test chính

| Test | Bắt | Ghi chú |
|---|---|---|
| `volume_anomalies` | Số dòng theo bucket thời gian bất thường | Cần `timestamp_column`, không có thì so tổng số dòng giữa các lần chạy |
| `freshness_anomalies` | Khoảng cách cập nhật bất thường | Theo `timestamp_column` |
| `event_freshness_anomalies` | Độ trễ giữa thời điểm sự kiện và thời điểm nạp | `event_timestamp_column` + `update_timestamp_column` |
| `column_anomalies` | Chỉ số của cột: `null_count`, `null_percent`, `zero_percent`, `min`, `max`, `average`, `standard_deviation`, `variance`, `missing_count`, `min_length`... | `column_anomalies: [null_percent]` |
| `all_columns_anomalies` | Như trên cho mọi cột | Tốn, dùng có chọn lọc |
| `dimension_anomalies` | Phân phối theo một chiều (số dòng theo `channel`) lệch | Bắt "app mất dữ liệu nhưng web bù lại" |
| `schema_changes` | Cột thêm/xoá/đổi kiểu so với **lần chạy trước** | Lần chạy đầu luôn pass (chưa có baseline) |
| `schema_changes_from_baseline` | So với schema khai báo trong YAML | Kiểu "contract cho source" |

Cú pháp với dbt ≥ 1.10 (tham số trong `arguments`):

```yaml
      - name: orders
        data_tests:
          - elementary.volume_anomalies:
              arguments:
                timestamp_column: order_ts
                time_bucket: {period: day, count: 1}
                training_period: {period: day, count: 30}
                detection_period: {period: day, count: 2}
                anomaly_direction: drop        # both (mặc định) | spike | drop
                anomaly_sensitivity: 3         # số độ lệch chuẩn
              config:
                severity: warn
```

## Anomaly detection hoạt động thế nào

1. Chia dữ liệu thành **bucket** (`time_bucket`, mặc định 1 ngày) theo `timestamp_column`.
2. Tính chỉ số cho từng bucket (số dòng, % NULL...) và lưu vào `data_monitoring_metrics`. Lần sau chỉ tính thêm bucket mới và tính lại vài bucket gần nhất (để đón dữ liệu về trễ).
3. Lấy các bucket trong **training_period** làm "bình thường": trung bình μ, độ lệch chuẩn σ.
4. Với mỗi bucket trong **detection_period**: z = (giá trị − μ) / σ. |z| > `anomaly_sensitivity` (mặc định 3) → anomaly.

Trong lab, ngày 2 có 32 đơn, trung bình ~119 → z ≈ −4 → `warn`. Ngày 3 phần còn lại về, bucket 02/12 được tính lại thành 106 đơn → `pass`.

"Bây giờ" của Elementary là `run_started_at` của dbt. Biến `custom_run_started_at` cho phép đặt giá trị khác (lab dùng biến này làm đồng hồ giả lập; ngoài đời dùng khi chạy lại một ngày cũ).

## Các bẫy đã gặp

- **`seasonality: day_of_week`** so bucket với **cùng thứ** của các tuần trước, nên cần lịch sử dài gấp nhiều lần. Trên lab 60 ngày, bật seasonality làm cửa sổ huấn luyện chứa các bucket **0 dòng** (trước khi có dữ liệu) → trung bình còn ~33 đơn/ngày → không phát hiện được ngày 2. Chỉ bật khi đủ lịch sử, và **đọc `test_results_description`** để kiểm tra.
- **`detection_period` dài** → một sự cố làm đỏ nhiều ngày liền (ngày 3 và ngày 4 với 2 ngày). Ngắn quá thì dữ liệu về trễ dễ làm báo nhầm.
- **Lần chạy đầu** của `schema_changes` luôn pass. Phải có lịch sử chạy.
- **Test trên source với severity error** làm skip mọi model phía sau (đã thấy trong lab với `not_null` trên `customer_id`).
- **Chi phí**: mỗi anomaly test là vài câu truy vấn trên bảng lớn. Giới hạn bằng `where`, chọn bảng quan trọng, không dùng `all_columns_anomalies` tràn lan.

## Đọc kết quả

```sql
select detected_at, test_type, test_sub_type, table_name, column_name, status,
       test_results_description
from dev_elementary.elementary_test_results
order by detected_at desc;

select bucket_start, metric_name, metric_value
from dev_elementary.data_monitoring_metrics
where full_table_name ilike '%orders%' and metric_name = 'row_count'
order by bucket_start desc;
```

## Câu hỏi tự kiểm tra

1. Tính z-score của ngày 2 trong lab với μ = 119, σ = 20. Với `anomaly_sensitivity: 3` thì sao? Với 5 thì sao?
2. Vì sao `dimension_anomalies` theo `channel` bắt được lỗi mà `volume_anomalies` bỏ sót?
3. Bạn có 60 ngày lịch sử, doanh số cuối tuần cao hơn 25%. Bật seasonality hay không? Còn cách nào khác?

## Tài liệu

- Elementary docs: *Anomaly detection tests*, *How anomaly detection works*, *Anomaly detection configuration* (training_period, detection_period, seasonality, sensitivity), *Elementary CLI / report*
