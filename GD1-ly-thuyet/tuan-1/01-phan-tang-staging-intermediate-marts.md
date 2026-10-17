# 1.1 Phân tầng: staging → intermediate → marts

## Khái niệm

Phân tầng (layering) là chia các model dbt thành nhiều lớp, mỗi lớp có **một trách nhiệm duy nhất**. Dữ liệu chảy một chiều từ nguồn thô sang dạng sẵn sàng cho business.

```
sources (raw)          staging                 intermediate                 marts
──────────────         ───────────────         ──────────────────────       ─────────────────────
Sales.SalesOrder... ─▶ stg_sales__orders ─┐
Sales.SalesOrder... ─▶ stg_sales__order_  ├──▶ int_orders__joined ────────▶ fct_sales
                        details           │                              ┌▶ dim_customers
Person.Person ───────▶ stg_person__people ┴──▶ int_customers__enriched ──┘
Production.Product ──▶ stg_production__products ─────────────────────────▶ dim_products
```

| Tầng | Trách nhiệm | Được làm | Không nên làm | Materialization thường dùng |
|---|---|---|---|---|
| **staging** | Làm sạch nguồn, 1:1 với bảng nguồn | rename cột, cast kiểu, đổi đơn vị, xử lý null/chuỗi rỗng, chọn cột | join, aggregate, logic business | `view` |
| **intermediate** | Các bước biến đổi trung gian, có mục đích cụ thể | join, pivot, tách/gộp grain, tính toán phức tạp | phơi ra cho BI dùng trực tiếp | `ephemeral` hoặc `view` |
| **marts** | Thực thể business, sẵn sàng dùng | fact, dimension, bảng tổng hợp theo phòng ban | đọc thẳng từ `source()` | `table` hoặc `incremental` |

## Tại sao cần

1. **DRY:** logic làm sạch chỉ viết một lần ở staging. Mọi model sau dùng `ref('stg_...')`, không ai chạm vào source lần nữa.
2. **Dễ debug:** lỗi số liệu thì lần ngược theo tầng, biết ngay lỗi ở bước nào.
3. **Thay nguồn ít đau:** nguồn đổi tên cột thì chỉ sửa staging.
4. **Rõ ranh giới cho người dùng:** BI/analyst chỉ được đọc marts.

## Quy ước đặt tên (theo dbt best practices)

| Tầng | Mẫu | Ví dụ |
|---|---|---|
| staging | `stg_<source>__<entity số nhiều>` | `stg_sales__orders`, `stg_person__people` |
| intermediate | `int_<entity>__<động từ>` | `int_orders__joined_details`, `int_customers__pivoted_addresses` |
| marts | `fct_<sự kiện>`, `dim_<thực thể>` | `fct_sales`, `dim_customers`, `dim_dates` |

Dấu `__` (2 gạch dưới) tách tên nguồn và tên thực thể, giúp đọc nhanh và select bằng wildcard.

## Cấu trúc folder

```
models/
├── staging/
│   ├── sales/
│   │   ├── _sales__sources.yml      # khai báo source
│   │   ├── _sales__models.yml       # docs + tests của stg
│   │   ├── stg_sales__orders.sql
│   │   └── stg_sales__order_details.sql
│   ├── person/
│   └── production/
├── intermediate/
│   └── sales/
│       └── int_orders__joined_details.sql
└── marts/
    ├── sales/
    │   ├── fct_sales.sql
    │   └── _sales__models.yml
    └── core/                        # dimension dùng chung
        ├── dim_customers.sql
        └── dim_dates.sql
```

Staging chia folder **theo nguồn** (source system). Marts chia **theo domain/phòng ban** (người dùng).

## Cấu hình materialization theo folder

```yaml
# dbt_project.yml
models:
  adventure_works:
    staging:
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: ephemeral
    marts:
      +materialized: table
      +schema: marts
```

Cấu hình ở `dbt_project.yml` áp cho cả folder; config trong file `.sql` (`{{ config(...) }}`) ghi đè khi cần.

## Mẫu model staging

```sql
-- models/staging/sales/stg_sales__orders.sql
with source as (
    select * from {{ source('sales', 'salesorderheader') }}
),

renamed as (
    select
        salesorderid                as order_id,
        customerid                  as customer_id,
        cast(orderdate as date)     as order_date,
        cast(duedate as date)       as due_date,
        status                      as order_status,
        subtotal                    as subtotal_amount,
        taxamt                      as tax_amount,
        freight                     as freight_amount,
        totaldue                    as total_due_amount,
        modifieddate                as modified_at
    from source
)

select * from renamed
```

Mẫu CTE `source → renamed → select` là quy ước cộng đồng: model nào cũng đọc được theo cùng một cách.

## Lỗi hay gặp

- Join ở staging → staging mất tính 1:1, khó tái sử dụng.
- Marts đọc thẳng `source()` → bỏ qua lớp làm sạch, logic bị lặp.
- Để intermediate là `table` khi không cần → tốn storage và thời gian build.
- `ephemeral` dùng quá nhiều → SQL compile ra rất dài, khó debug; không query trực tiếp được. Nếu cần debug thì tạm đổi sang `view`.
- Đặt tên lẫn lộn (`orders_clean`, `final_orders`) → người khác không đoán được tầng.

## Áp dụng vào adventure_works

- [ ] Khai báo sources cho các schema `Sales`, `Person`, `Production` (dùng codegen — xem 1.2)
- [ ] Mỗi bảng nguồn dùng tới có đúng 1 model `stg_`
- [ ] Ít nhất 2 model `int_` có lý do tồn tại rõ ràng
- [ ] `fct_sales` (grain: 1 dòng = 1 order line), `dim_customers`, `dim_products`, `dim_dates`
- [ ] Cấu hình materialization theo folder trong `dbt_project.yml`
- [ ] Ghi grain của mỗi fact vào description

## Câu hỏi tự kiểm tra

1. Vì sao staging thường là `view` còn marts là `table`?
2. Khi nào một phép join được phép xuất hiện ở staging? (gợi ý: bảng nguồn bị tách đôi một cách kỹ thuật, ví dụ bảng chính + bảng mở rộng 1:1)
3. `ephemeral` khác `view` thế nào? Nhược điểm của `ephemeral`?
4. Nếu nguồn đổi tên `totaldue` thành `total_due`, bạn phải sửa bao nhiêu file?

## Tài liệu

- dbt docs — *How we structure our dbt projects*: https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview
- dbt docs — Materializations: https://docs.getdbt.com/docs/build/materializations
