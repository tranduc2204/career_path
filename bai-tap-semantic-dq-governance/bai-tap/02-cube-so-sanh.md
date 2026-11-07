# 02 — Dựng thử Cube trên cùng dữ liệu, viết bài so sánh (không chấm)

> Lý thuyết: [GD3-ly-thuyet/tuan-8/05-cube-va-so-sanh.md](../../GD3-ly-thuyet/tuan-8/05-cube-va-so-sanh.md). Làm sau M1–M8.
> Đã chạy thử 07/11/2026: Cube Core **v1.6.77**, driver DuckDB, trên bản sao `lab.duckdb`. Doanh thu tháng 10 và 11 ra **đúng bằng** kết quả MetricFlow.

Bạn đã có 15 metric trong MetricFlow. Bài này dựng lại khoảng 6 metric đó bằng **Cube**, một semantic layer độc lập với dbt, để trả lời câu hỏi phỏng vấn kinh điển: *"Semantic layer của dbt hay Cube, khi nào chọn cái nào?"*

## 1. Chạy Cube

Cần Docker.

```bash
cd lab
dbt build                       # đảm bảo mart (và dim_customers_v2 nếu đã làm G4) đã có
./cube/snapshot.sh              # chép lab.duckdb → cube/data/mayshop.duckdb
cd cube && docker compose up    # lần đầu tải image ~330 MB
```

- Playground: http://localhost:4000 (chọn measure/dimension bằng chuột, xem SQL sinh ra, xem JSON)
- REST: `python query.py '{"measures":["orders.count","orders.aov"],"dimensions":["orders.channel"]}'`
- SQL API (giao thức Postgres): `psql -h localhost -p 15432 -U cube` (mật khẩu `cube`), rồi `select channel, measure(aov) from orders group by 1;`

Vì sao phải dùng bản sao? DuckDB chỉ cho **một tiến trình ghi**. Cube mở file trong lúc bạn còn chạy `dbt` thì một trong hai sẽ lỗi khoá. Với warehouse thật (Snowflake, BigQuery) thì không có vấn đề này.

Nếu chưa làm G4 (chưa có `dim_customers_v2`), sửa `sql_table` của cube `customers` trong `model/cubes/dims.yml` thành `dev_marts.dim_customers`.

## 2. Kit có sẵn

```
cube/
├── docker-compose.yml
├── model/cubes/orders.yml        ← count, buyers, items_amount, aov + 1 pre-aggregation
├── model/cubes/order_items.yml   ← revenue (lọc đơn huỷ qua join), cogs, gross_profit
├── model/cubes/dims.yml          ← products, customers, marketing_channels
└── model/views/sales.yml         ← view: giao diện gọn cho BI
```

Đọc và so với YAML MetricFlow của bạn:

| Ý tưởng | MetricFlow | Cube |
|---|---|---|
| Đơn vị mô hình | semantic model trên 1 model dbt | cube trên 1 bảng / 1 câu SQL |
| Quan hệ | **entity** (khoá), MetricFlow tự tìm đường join | **joins** khai báo tường minh + `relationship` |
| Đơn đã huỷ | `filter` dùng `Dimension('sales_order__is_cancelled')` | `filters: - sql: "{orders.is_cancelled} = false"` |
| Ratio | `type: ratio` (numerator/denominator) | `type: number` với `sql: "{a} / NULLIF({b}, 0)"` |
| Cumulative | `type: cumulative`, `window`, `grain_to_date` | `rolling_window` trên measure |
| Tăng tốc | (dựa vào warehouse / exports trên Cloud) | **pre_aggregations** + Cube Store |
| Giao diện cho BI | saved query, JDBC / GraphQL (dbt platform) | REST, GraphQL, **SQL API kiểu Postgres**, MDX/DAX (bản thương mại) |

## 3. Việc cần làm

1. Thêm vào Cube: `refunds` (cube mới trên `fct_refunds`, thời gian = `refund_date`), `net_revenue`, `revenue_mtd` (dùng `rolling_window: {type: to_date, granularity: month}`), `roas` theo `marketing_channels.channel_group`.
2. Với mỗi metric, so kết quả Cube với `mf query` trên cùng khoảng ngày (01/10 → 30/11). Ghi lại chỗ nào khớp, chỗ nào lệch và vì sao.
3. Thử 2 câu khó:
   - `net_revenue` theo ngày khi có ngày không có hoàn tiền. Cube xử lý NULL thế nào?
   - `roas` theo nhóm kênh: Cube cần đường join nào giữa `order_items`, `ad_spend` và `marketing_channels`? Có bị **fan-out** (nhân dòng) không? (Gợi ý: đọc tài liệu Cube về "multi-fact" / view có nhiều `join_path`.)
4. Bật pre-aggregation `daily_by_channel`, chạy cùng một truy vấn 2 lần, xem log Cube cho biết nó có đọc từ pre-aggregation không.

## 4. Bài viết so sánh (sản phẩm của tuần 8)

Viết `docs/semantic-layer-metricflow-vs-cube.md` (hoặc bài blog), 800–1.200 chữ, theo khung:

1. **Bối cảnh:** Mây Shop có 3 đội, 15 metric, dashboard trên BI + 1 trợ lý AI (tuần 14 sẽ làm).
2. **Mô hình hoá:** cùng 6 metric, hai bên viết khác nhau ở đâu (dán 2 đoạn YAML ngắn).
3. **Kết quả:** bảng đối chiếu số liệu, các chỗ lệch và nguyên nhân.
4. **Vận hành:** CI (`mf validate-configs` vs `cube` build), versioning, quyền truy cập theo hàng (Cube có `query_rewrite` / access policy), cache, chi phí.
5. **Khi nào chọn cái nào:** ít nhất 3 tình huống cho mỗi bên.
6. **Quyết định cho Mây Shop** viết dưới dạng ADR ngắn (bối cảnh, lựa chọn, hệ quả).

## Câu hỏi tự kiểm tra

1. Vì sao MetricFlow không cần bạn khai báo đường join, còn Cube thì cần? Lợi và hại của mỗi cách?
2. Pre-aggregation của Cube giải quyết vấn đề gì mà một bảng mart tổng hợp sẵn không giải quyết được?
3. Nếu công ty đã có Looker (LookML), bạn có đề xuất thêm dbt Semantic Layer không? Lập luận.
