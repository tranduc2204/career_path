# 7.2 Snowflake: Query Profile, pruning, clustering

## Snowflake lưu dữ liệu thế nào

```
Bảng ──▶ hàng nghìn MICRO-PARTITION (mỗi cái 50–500 MB dữ liệu chưa nén, lưu dạng cột, nén, bất biến)
              │
              └── metadata của từng micro-partition: min/max mỗi cột, số giá trị khác nhau, số null...
```

**Pruning**: khi query có `where order_date between '2026-03-01' and '2026-03-07'`, Snowflake đọc metadata, **bỏ qua** mọi micro-partition có khoảng `[min, max]` của `order_date` không giao với khoảng lọc. Không đọc = không tốn thời gian.

Pruning tốt khi dữ liệu **được sắp xếp tự nhiên** theo cột lọc. Dữ liệu nạp theo ngày thì thường đã gọn theo ngày (natural clustering). Lọc theo cột "lộn xộn" (mã khách ngẫu nhiên) thì gần như mọi micro-partition đều chứa giá trị cần tìm → không prune được.

Pruning cũng xảy ra theo **cột**: chỉ đọc cột được dùng (columnar).

## Ba tầng cache

| Cache | Ở đâu | Còn khi nào | Ghi chú |
|---|---|---|---|
| **Result cache** | Cloud services | 24h, nếu query giống hệt và dữ liệu không đổi | Không cần warehouse, miễn phí. Tắt khi đo: `ALTER SESSION SET USE_CACHED_RESULT = FALSE;` |
| **Warehouse cache** (local disk) | SSD của warehouse | Mất khi warehouse suspend | Lý do không đặt `AUTO_SUSPEND` quá ngắn cho BI |
| **Metadata** | Cloud services | Luôn | `count(*)`, `min/max` toàn bảng trả lời từ metadata, không quét |

## Query Profile: đọc thế nào

Mở: Snowsight → **Monitoring → Query History** → chọn query → tab **Query Profile**.

```
                [Result]
                   │
              [Aggregate]
                   │
               [Join] ◀──── xem số dòng vào/ra: ra >> vào = exploding join
              /       \
     [TableScan]    [TableScan]   ◀── xem Partitions scanned / Partitions total
        ORDERS       LINEITEM
```

Bên phải là **Most Expensive Nodes** (các bước chiếm ≥ 1% thời gian, xếp giảm dần) và các nhóm thống kê:

| Thống kê | Đọc thế nào |
|---|---|
| **Pruning**: Partitions scanned / Partitions total | Tỷ lệ càng nhỏ càng tốt. Scanned ≈ total khi có filter = **pruning kém** |
| **Spilling**: Bytes spilled to local storage / remote storage | Dữ liệu trung gian không vừa bộ nhớ, phải ghi ra đĩa. Remote spill = **rất chậm** |
| **IO**: Percentage scanned from cache | Tỷ lệ đọc từ warehouse cache |
| **IO**: Bytes scanned | Tổng byte đọc |
| **Network**: Bytes sent over the network | Dữ liệu chuyển giữa các node (join/aggregate lớn) |

Bốn vấn đề Snowflake gọi tên trong tài liệu Query Profile:

| Vấn đề | Dấu hiệu | Xử lý |
|---|---|---|
| **Exploding join** | Node Join xuất ra nhiều dòng hơn nhiều so với đầu vào | Kiểm tra điều kiện join, grain 2 phía |
| **UNION không ALL** | Có thêm bước loại trùng | Dùng `UNION ALL` nếu không cần loại trùng |
| **Query quá lớn so với bộ nhớ** | Spilling, đặc biệt remote | Warehouse lớn hơn, hoặc xử lý theo lô nhỏ hơn |
| **Pruning kém** | Partitions scanned ≈ total | Tổ chức lại dữ liệu (sắp xếp / clustering key), sửa filter |

## Clustering key

### Khi nào cần

Theo tài liệu Snowflake, clustering key thường chỉ đáng khi:
- Bảng **rất lớn** (thường vài TB trở lên).
- Query thường **lọc hoặc sắp xếp** theo cột đó.
- Query Profile cho thấy pruning kém.

Bảng vài GB: thường **không cần**. Snowflake đã tự gom dữ liệu theo thứ tự nạp.

### Định nghĩa

```sql
create table fct_sales (...) cluster by (order_date);
alter table fct_sales cluster by (order_date, store_id);
alter table fct_sales drop clustering key;
```

Chọn cột:
- Tối đa **3–4 cột / biểu thức**.
- Sắp **từ cardinality thấp tới cao**.
- Cột cardinality cực cao (id duy nhất, timestamp tới mili giây) → dùng biểu thức thu gọn: `to_date(created_at)`, `substring(sku, 1, 3)`.
- Cột cardinality cực thấp (boolean) prune được rất ít.

### Automatic Clustering tốn tiền

Khi bảng có clustering key, dịch vụ **Automatic Clustering** chạy nền, sắp xếp lại micro-partition khi dữ liệu thay đổi. Nó **tốn credit** (serverless, không thuộc warehouse của bạn, không bị resource monitor của warehouse chặn) và **tăng storage** (micro-partition cũ còn trong Time Travel/Fail-safe). Bảng thay đổi liên tục + clustering key = chi phí nền liên tục.

### Đo độ "gọn"

```sql
select system$clustering_information('analytics.marts.fct_sales', '(order_date)');
```

Trả về JSON, các trường hay xem:

| Trường | Ý nghĩa |
|---|---|
| `total_partition_count` | Số micro-partition |
| `average_overlaps` | Trung bình mỗi micro-partition chồng khoảng giá trị với bao nhiêu cái khác |
| `average_depth` | Độ sâu chồng lấn trung bình. **Càng gần 1 càng gọn** |
| `partition_depth_histogram` | Phân bố độ sâu |

### Trong dbt

```sql
{{ config(materialized='table', cluster_by=['order_date']) }}
```

dbt-snowflake làm 2 việc: thêm `order by order_date` vào câu `create table as` (bảng sinh ra **đã gọn** sẵn) và `alter table ... cluster by (order_date)`. Với incremental, dbt sắp xếp dữ liệu staging trước khi merge. Config `automatic_clustering` chỉ có tác dụng với tài khoản còn dùng chế độ clustering thủ công (đã ngừng hỗ trợ); tài khoản bình thường tự động.

Cách rẻ hơn cho bảng vừa: **chỉ sắp xếp khi tạo bảng** (`order by` trong model `table` dựng lại hằng ngày) mà không đặt clustering key → được pruning tốt, không tốn Automatic Clustering.

## Các công cụ khác (biết tên)

| Công cụ | Dùng khi |
|---|---|
| **Search Optimization Service** | Tra cứu điểm (`where email = 'x'`) trên bảng lớn. Tốn phí riêng |
| **Query Acceleration Service** | Một phần query quét lớn được tăng tốc bằng tài nguyên serverless |
| **Materialized view** | Tổng hợp dùng lại nhiều lần (bản Enterprise trở lên) |
| **Dynamic table** | Bảng tự làm mới theo độ trễ mục tiêu |

## Lỗi hay gặp

- Đặt clustering key cho bảng vài GB.
- Clustering key trên cột ngẫu nhiên cardinality cực cao.
- Quên Automatic Clustering tốn credit nền.
- Đo hiệu năng khi result cache đang bật.
- Bọc cột lọc trong hàm làm khó pruning.
- Thấy spill thì chỉ biết tăng cỡ warehouse, không xem có exploding join không.

## Áp dụng vào adventure_works

Tuần 7 dùng thêm dữ liệu mẫu `SNOWFLAKE_SAMPLE_DATA` (TPC-H, nhiều kích cỡ) vì AdventureWorks quá nhỏ để thấy pruning. Bài thí nghiệm chi tiết: [bai-tap-performance/snowflake](../../bai-tap-performance/snowflake/).

- [ ] Mở Query Profile của 3 model chậm nhất trong `adventure_works`, ghi lại node đắt nhất, pruning, spill
- [ ] Thí nghiệm sắp xếp vs không sắp xếp trên bảng TPC-H, ghi Partitions scanned / total
- [ ] `system$clustering_information` trước và sau khi sắp xếp
- [ ] Kết luận vào playbook: adventure_works có model nào **đáng** đặt clustering key không? (Câu trả lời trung thực có thể là "không, vì bảng chỉ vài trăm MB")

## Câu hỏi tự kiểm tra

1. Micro-partition là gì? Metadata của nó giúp pruning thế nào?
2. Ba tầng cache của Snowflake? Tắt cache khi đo thế nào?
3. Trong Query Profile, dấu hiệu của pruning kém, spilling, exploding join là gì?
4. Khi nào đáng đặt clustering key? Chọn cột theo nguyên tắc nào?
5. Automatic Clustering tốn tiền ở đâu?
6. `cluster_by` trong dbt-snowflake sinh ra những câu lệnh gì?

## Tài liệu

- Micro-partitions & data clustering: https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions
- Clustering keys & clustered tables: https://docs.snowflake.com/en/user-guide/tables-clustering-keys
- Query Profile (Monitor query activity): https://docs.snowflake.com/en/user-guide/ui-snowsight-activity
- dbt-snowflake configs (`cluster_by`, `snowflake_warehouse`, `query_tag`): https://docs.getdbt.com/reference/resource-configs/snowflake-configs
