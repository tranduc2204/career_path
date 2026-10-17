# 3.6 Source freshness

## Khái niệm

**Freshness** kiểm tra **dữ liệu nguồn có còn mới không**: lần cuối dữ liệu được nạp là khi nào, có quá ngưỡng cho phép không.

Tình huống: pipeline ingest (Airbyte/Fivetran/dlt) chết từ 3 ngày trước, dbt vẫn chạy "thành công" mỗi ngày trên dữ liệu cũ → dashboard sai mà không ai biết. Freshness bắt được lỗi này.

## Cú pháp

```yaml
# models/staging/sales/_sales__sources.yml
sources:
  - name: sales
    database: adventure_works
    schema: sales
    loaded_at_field: _loaded_at              # cột thời gian nạp
    freshness:                               # mặc định cho mọi bảng trong source
      warn_after: { count: 12, period: hour }
      error_after: { count: 24, period: hour }
    tables:
      - name: salesorderheader
      - name: salesorderdetail
        loaded_at_field: modifieddate        # ghi đè cho bảng này
      - name: currency
        freshness: null                      # bảng tham chiếu, không cần kiểm
```

- `period`: `minute`, `hour`, `day`.
- Ghi chú phiên bản: dbt mới hơn (1.10+) khuyến khích đặt `freshness` và `loaded_at_field` bên trong `config:` của source/table. Cú pháp trên vẫn chạy nhưng có thể báo deprecation — kiểm tra theo version bạn cài.

Chạy:

```bash
dbt source freshness                       # mọi source
dbt source freshness --select source:sales # 1 source
```

Kết quả: `PASS` / `WARN` / `ERROR`, ghi vào `target/sources.json`.

## Cách dbt tính

```sql
select max(<loaded_at_field>) as max_loaded_at, current_timestamp as snapshotted_at
from <bảng nguồn>
```

So `snapshotted_at - max_loaded_at` với ngưỡng warn/error.

- Bảng rất lớn: thêm `filter` để chỉ quét dữ liệu gần đây, giảm chi phí.
- Một số adapter (Snowflake, BigQuery...) lấy được thời điểm cập nhật từ **metadata** của bảng khi không khai `loaded_at_field`.

## Chọn `loaded_at_field`

| Ưu tiên | Cột | Lý do |
|---|---|---|
| 1 | Cột do công cụ ingest thêm (`_loaded_at`, `_airbyte_extracted_at`, `_dlt_load_id`...) | Phản ánh đúng **lúc nạp** |
| 2 | `modified_at` / `updated_at` của nguồn | Gần đúng, nhưng là thời gian **sửa ở nguồn** |
| ❌ | `order_date` (event time) | Ngày lễ không có đơn → báo stale sai |

## Chọn ngưỡng

Dựa trên **lịch nạp** + SLA: nguồn nạp mỗi 6h → warn 12h, error 24h. Ngưỡng quá chặt → báo động giả; quá lỏng → phát hiện muộn.

## Freshness trong pipeline

1. **Chặn build khi nguồn cũ:** chạy `dbt source freshness` trước `dbt build`; lỗi thì dừng.
2. **Chỉ build phần có dữ liệu mới:**
   ```bash
   dbt source freshness
   dbt build --select source_status:fresher+ --state ./prev-artifacts
   ```
   `source_status:fresher+` chọn các source có dữ liệu mới hơn so với lần chạy trước (so `sources.json`) và downstream của chúng.

## AdventureWorks — lưu ý

Dữ liệu mẫu là **tĩnh** (dừng ở 2014), nên freshness sẽ luôn ERROR nếu dùng `modifieddate`. Cách xử lý cho portfolio:
- Thêm cột `_loaded_at` khi nạp (nếu bạn tự load bằng dlt/script), hoặc
- Có script giả lập nạp dữ liệu mới định kỳ, hoặc
- Ghi rõ trong README: cấu hình freshness minh hoạ, ngưỡng thực tế sẽ đặt theo SLA.

## Lỗi hay gặp

- Dùng event time làm `loaded_at_field`.
- Không khai `freshness: null` cho bảng tham chiếu ít đổi → warning liên tục, team lờ đi.
- Chạy freshness nhưng không ai đọc kết quả (không có alert).

## Áp dụng vào adventure_works

- [ ] Freshness cho các source chính, `freshness: null` cho bảng tham chiếu
- [ ] Giải quyết vấn đề dữ liệu tĩnh (1 trong 3 cách ở trên)
- [ ] Workflow (cron trên GitHub Actions) chạy `dbt source freshness` mỗi ngày
- [ ] README: bảng source – lịch nạp – ngưỡng warn/error

## Câu hỏi tự kiểm tra

1. Freshness bắt được lỗi gì mà data test không bắt?
2. Vì sao không nên dùng `order_date` làm `loaded_at_field`?
3. `source_status:fresher+` chọn những gì?
4. Kết quả freshness ghi vào file nào?

## Tài liệu

- https://docs.getdbt.com/docs/deploy/source-freshness
- https://docs.getdbt.com/reference/resource-properties/freshness
- https://docs.getdbt.com/reference/node-selection/methods#source_status
