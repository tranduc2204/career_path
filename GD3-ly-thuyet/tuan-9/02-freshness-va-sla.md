# 9.2 Freshness và SLA

## SLA, SLO, SLI

| | Nghĩa | Ví dụ Mây Shop |
|---|---|---|
| **SLI** (indicator) | Thứ đo được | Tuổi dữ liệu mới nhất của `fct_orders` lúc 07:00 |
| **SLO** (objective) | Mục tiêu nội bộ cho SLI | ≥ 99% ngày trong tháng, `fct_orders` có dữ liệu hôm qua trước 07:00 |
| **SLA** (agreement) | Cam kết với người dùng, kèm hệ quả | "Dashboard doanh thu có số hôm qua trước 08:00. Nếu trễ, đội dữ liệu báo trên kênh #finance trước 08:15" |

SLA đặt **ngược từ người dùng**: Finance mở dashboard 08:00 → mart xong trước 07:30 → dbt chạy 06:30 → connector xong trước 06:15. Mỗi tầng có ngưỡng riêng.

## Source freshness trong dbt

```yaml
sources:
  - name: shop
    config:
      freshness:
        warn_after:  {count: 12, period: hour}
        error_after: {count: 36, period: hour}
      loaded_at_field: _loaded_at          # cột thời điểm nạp
    tables:
      - name: orders
      - name: refunds
        config:
          loaded_at_query: >               # dbt ≥ 1.10: câu SQL trả về "lần nạp gần nhất"
            select max(synced_at) from {{ source('ingest', 'sync_log') }}
            where table_name = 'shop.refunds' and status = 'success'
      - name: some_static_table
        config:
          freshness: null                  # tắt hẳn
```

```bash
dbt source freshness                       # ghi target/sources.json
dbt source freshness -s source:shop
dbt build -s "source_status:fresher+" --state prod-artifacts   # chỉ build phần có nguồn mới hơn lần trước
```

dbt tính `max(loaded_at_field)` (hoặc chạy `loaded_at_query`), so với `current_timestamp()` của warehouse, rồi trả `pass` / `warn` / `error`. Lab ghi đè `current_timestamp()` bằng đồng hồ giả lập ([00-setup](../../bai-tap-semantic-dq-governance/bai-tap/00-setup.md#4-đồng-hồ-của-lab)).

## Chọn cột đo: "dữ liệu mới" hay "connector còn sống"

| Đo theo | Trả lời câu hỏi | Bẫy |
|---|---|---|
| `_loaded_at` / `_fivetran_synced` / `_airbyte_extracted_at` | Lần cuối có **dòng mới** về là khi nào? | Bảng ít đổi (sản phẩm) hoặc thưa (hoàn tiền) → báo động giả dù connector vẫn chạy |
| Cột nghiệp vụ (`order_ts`) | Sự kiện mới nhất xảy ra khi nào? | Lệch múi giờ; dữ liệu đến muộn làm tưởng tươi |
| Nhật ký sync (`fivetran_audit`, `ingest.sync_log`) qua `loaded_at_query` | Connector chạy thành công lần cuối khi nào? | Phải lọc `status = 'success'`. Connector "thành công" nhưng 0 dòng vẫn có thể là sự cố (dùng volume) |

Lab gài đúng 2 bẫy này: `erp.products` gần như không đổi (đỏ ngay ngày 0), `shop.refunds` có ngày 0 dòng (đỏ ngày 7, vốn là ngày sạch).

## Freshness ở các tầng khác

- **Elementary `freshness_anomalies` / `event_freshness_anomalies`**: học khoảng cách cập nhật thường ngày, báo khi lệch. Hợp với nguồn không có lịch cố định.
- **Model freshness** (dbt ≥ 1.10, `config: freshness: build_after:`) phục vụ orchestration "chỉ build khi nguồn có dữ liệu mới" trên dbt platform. Khác source freshness: nó điều khiển **khi nào build**, không phải cảnh báo.
- **Orchestrator**: sensor đợi nguồn sẵn sàng rồi mới chạy (Airflow sensor, Dagster sensor / declarative automation), thay vì chạy cố định 06:30 rồi báo lỗi.

## Viết SLA cho một mart

```yaml
  - name: fct_orders
    config:
      meta:
        owner: commerce-data@mayshop.vn
        sla: "Dữ liệu tới hết hôm qua có trước 07:00 (GMT+7), 99% ngày/tháng"
        sla_source_freshness: {warn_after_hours: 12, error_after_hours: 36}
        consumers: [daily_revenue_dashboard]
```

`meta` không được dbt thực thi, nhưng hiện trên docs, catalog (OpenMetadata) và đọc được bằng script (CI kiểm tra mọi model public có `meta.sla`).

## Câu hỏi tự kiểm tra

1. Vì sao ngưỡng `warn_after: 12h` lại hợp lý cho pipeline nạp 1 lần/ngày lúc 06:00 và dbt chạy 06:30?
2. Connector báo `success` với 0 dòng ba ngày liền. Freshness theo sync_log có bắt được không? Cái gì bắt được?
3. Thiết kế SLA từ dưới lên cho dashboard Finance mở lúc 08:00.

## Tài liệu

- dbt docs: *Source freshness*, *freshness config* (`loaded_at_field`, `loaded_at_query`, `filter`), *source_status selector*
- Google SRE Book, chương *Service Level Objectives* (SLI/SLO/SLA gốc từ đây)
