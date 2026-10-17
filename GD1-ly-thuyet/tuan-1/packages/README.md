# Học sâu 3 package: dbt-utils, codegen, dbt-expectations

> Phần mở rộng của [02-dbt-packages.md](../02-dbt-packages.md). File đó là tổng quan; folder này đi vào từng macro, từng test.

## Mỗi package giải quyết việc gì

| Package | Vai trò | Chạy ở đâu | Ra gì |
|---|---|---|---|
| [dbt-utils](01-dbt-utils.md) | "Thư viện chuẩn": macro sinh SQL + generic test thông dụng | Trong model, trong YAML test | SQL nằm trong model/test |
| [codegen](02-codegen.md) | Sinh code boilerplate (YAML, SQL) | `dbt run-operation` trên terminal | Text in ra để bạn lưu vào file |
| [dbt-expectations](03-dbt-expectations.md) | ~60 test chất lượng dữ liệu kiểu Great Expectations | Trong YAML test | Test chạy khi `dbt test`/`dbt build` |

```
         codegen                    dbt-utils                        dbt-expectations
   (lúc VIẾT code, 1 lần)     (lúc BUILD, trong model)           (lúc TEST, sau khi build)
 ┌────────────────────────┐  ┌─────────────────────────────┐   ┌──────────────────────────────┐
 │ generate_source        │  │ generate_surrogate_key      │   │ khoảng giá trị, regex,       │
 │ generate_base_model    │─▶│ star, date_spine, pivot...  │──▶│ số dòng, phân phối, độ tươi, │
 │ generate_model_yaml    │  │ + test: unique_combination… │   │ schema, so sánh 2 bảng       │
 └────────────────────────┘  └─────────────────────────────┘   └──────────────────────────────┘
```

## Thứ tự học đề xuất (khoảng 3 buổi sáng)

| Buổi | Nội dung | Thực hành trên adventure_works |
|---|---|---|
| 1 | codegen (ngắn) + nhóm SQL generator của dbt-utils | Sinh sources + staging cho schema `sales`; `dim_dates` bằng `date_spine`; surrogate key cho `fct_sales` |
| 2 | Nhóm introspective + generic test của dbt-utils | `pivot` doanh thu theo territory; 5 test dbt-utils trên marts |
| 3 | dbt-expectations | 6–8 test ở nhiều nhóm khác nhau; 1 test anomaly |

## Mẹo học package hiệu quả

1. **Đọc source code.** Sau `dbt deps`, toàn bộ code nằm trong `dbt_packages/<tên>/macros/`. Mở `dbt_packages/dbt_utils/macros/sql/star.sql` đọc 30 dòng sẽ hiểu hơn đọc docs 10 lần.
2. **Xem SQL đã compile.** Chạy `dbt compile -s <model>` rồi mở `target/compiled/...`. Với test: `target/compiled/adventure_works/models/.../<tên_test>.sql`.
3. **Học chi tiết `adapter.dispatch`.** Mọi macro đều có dạng `{{ return(adapter.dispatch('star', 'dbt_utils')(...)) }}` → `default__star`. Đây là mẫu sẽ dùng khi tự viết package ở tuần 13.
4. **Biết đủ, không cần thuộc hết.** Mục tiêu là biết package có gì, để khi gặp vấn đề thì nhớ ra "cái này dbt-utils có rồi" thay vì tự viết lại.

## Tài liệu gốc

- https://hub.getdbt.com/dbt-labs/dbt_utils/latest/ — README của dbt-utils là tài liệu đầy đủ nhất
- https://hub.getdbt.com/dbt-labs/codegen/latest/
- https://github.com/metaplane/dbt-expectations
