# 8.5 Cube và so sánh với dbt Semantic Layer

> Kit chạy thử: [bai-tap/02-cube-so-sanh.md](../../bai-tap-semantic-dq-governance/bai-tap/02-cube-so-sanh.md) (Cube Core v1.6.77 + DuckDB, đã chạy 07/11/2026).

## Cube là gì

Cube là semantic layer **độc lập** (mã nguồn mở Cube Core + bản thương mại Cube Cloud). Nó là một server đứng giữa warehouse và các ứng dụng:

```
warehouse ──▶ Cube (data model YAML/JS) ──▶ REST · GraphQL · SQL API (Postgres) · MDX/DAX*
                 │ cache / pre-aggregations (Cube Store)
                 └ access control theo hàng / cột (security context)        * bản thương mại
```

## Data model của Cube

```yaml
cubes:
  - name: order_items
    sql_table: dev_marts.fct_order_items
    joins:
      - name: orders
        sql: "{CUBE}.order_id = {orders}.order_id"
        relationship: many_to_one          # one_to_one, one_to_many, many_to_one
    dimensions:
      - name: order_item_id
        sql: order_item_id
        type: string
        primary_key: true                   # bắt buộc để Cube chống fan-out
      - name: order_date
        sql: order_date
        type: time
    measures:
      - name: revenue
        type: sum
        sql: line_amount
        filters:
          - sql: "{orders.is_cancelled} = false"
      - name: revenue_mtd
        type: sum
        sql: line_amount
        rolling_window: {type: to_date, granularity: month}

views:                                       # "giao diện" cho người dùng
  - name: sales
    cubes:
      - join_path: order_items
        includes: [revenue, order_date]
      - join_path: order_items.orders
        prefix: true
        includes: [count, aov, channel]
```

- **cube** ≈ semantic model (một bảng hoặc một câu SQL).
- **joins** khai báo **tường minh** kèm `relationship`. Khác MetricFlow (tự suy ra từ entity).
- **measure** ≈ metric. `type: number` + `sql: "{a} / NULLIF({b}, 0)"` là ratio. `rolling_window` là cumulative.
- **view** chọn đường join và các trường được phơi ra. Đây là thứ BI nhìn thấy.
- **pre_aggregations**: Cube tự dựng bảng tổng hợp (lưu ở Cube Store), làm mới theo lịch, và **tự định tuyến** truy vấn vào đó khi khớp. Đây là điểm mạnh lớn nhất của Cube với dashboard nhiều người xem.

## So sánh

| Tiêu chí | dbt Semantic Layer (MetricFlow) | Cube |
|---|---|---|
| Nằm ở đâu | Cạnh model dbt, cùng repo, cùng PR | Server riêng (có thể cùng repo) |
| Join | Tự suy từ entity, chặn fan-out theo loại entity | Khai báo `joins` + `relationship`, chống fan-out nhờ `primary_key` |
| Loại metric | simple, ratio, derived (có offset), cumulative, conversion | sum/count/..., `number` (tự viết), `rolling_window`. Kỳ trước / phễu phải tự dựng (hoặc multi-stage measures) |
| Thời gian | `metric_time` thống nhất cho mọi metric | Mỗi truy vấn chọn time dimension của cube |
| Cache | dbt platform (saved query cache), `exports` | **Pre-aggregation + Cube Store**, rất mạnh |
| API | JDBC/ADBC, GraphQL (platform); `mf` (Core) | REST, GraphQL, **SQL API Postgres** (BI nào cũng nối được), có ở bản mã nguồn mở |
| Phân quyền | Theo quyền của warehouse / platform | **Security context**: lọc theo hàng/cột theo người hỏi |
| Chi phí | MetricFlow miễn phí; API cần dbt platform | Cube Core miễn phí (tự vận hành); Cube Cloud trả phí |
| Vận hành | Không thêm server (Core) | Thêm 1 dịch vụ (API + refresh worker + Cube Store) |
| Hợp với | Đội dbt-first, metric gắn chặt với model | Embedded analytics, nhiều app tiêu thụ, cần cache và quyền theo hàng |

## Gợi ý khung quyết định

- Đã dùng dbt platform và BI tích hợp sẵn → **dbt Semantic Layer**.
- Dùng dbt Core, cần API cho ứng dụng / dashboard nhúng cho khách hàng, cần phân quyền theo tenant → **Cube**.
- Có Looker và mọi người chỉ dùng Looker → LookML là semantic layer. Thêm tầng nữa chỉ khi có người tiêu thụ ngoài Looker (AI agent, notebook).
- Đừng định nghĩa cùng metric ở 2 nơi lâu dài. Nếu buộc phải có cả hai, chọn **một nơi là nguồn**, nơi kia sinh ra từ đó, và có test đối chiếu số.

## Câu hỏi tự kiểm tra

1. Pre-aggregation của Cube khác bảng mart tổng hợp ở điểm nào? (gợi ý: định tuyến tự động, làm mới theo partition)
2. Cube chống fan-out bằng cách nào khi `sum` một measure qua join one-to-many?
3. Bạn trình bày cho CTO trong 2 phút: vì sao Mây Shop chọn công cụ X. Viết ra.

## Tài liệu

- Cube docs: *Data modeling* (cubes, views, joins, measures), *Pre-aggregations*, *SQL API*, *Security context*
- Cube docs: *DuckDB* (driver). Các bài so sánh do chính nhà cung cấp viết (Cube, dbt Labs) nên đọc với con mắt phê phán
