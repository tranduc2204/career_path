# 2.4 Custom generic test

## Các loại test trong dbt

| Loại | Định nghĩa | Tái sử dụng | Ví dụ |
|---|---|---|---|
| **Generic test có sẵn** | `unique`, `not_null`, `accepted_values`, `relationships` | ✅ | `not_null` trên `order_id` |
| **Generic test từ package** | dbt-utils, dbt-expectations | ✅ | `dbt_utils.accepted_range` |
| **Custom generic test** | Bạn tự viết, có tham số | ✅ | `is_positive`, `valid_date_range` |
| **Singular test** | 1 file SQL trong `tests/`, dùng 1 lần | ❌ | Kiểm tra tổng doanh thu khớp nguồn |
| **Unit test** (dbt ≥ 1.8) | Kiểm tra **logic SQL** với input giả | — | Kiểm tra cách tính `net_amount` |

> Data test kiểm tra **dữ liệu** (chạy trên dữ liệu thật). Unit test kiểm tra **code** (chạy trên input giả). Tuần 2 tập trung data test.

## Nguyên lý cốt lõi

**Test = câu `select` trả về các dòng vi phạm.** 0 dòng → pass, ≥ 1 dòng → fail (hoặc warn).

## Cú pháp custom generic test

Đặt trong `tests/generic/` (hoặc `macros/`):

```sql
-- tests/generic/test_is_positive.sql
{% test is_positive(model, column_name, allow_zero=false) %}

select *
from {{ model }}
where {{ column_name }} {% if allow_zero %} < 0 {% else %} <= 0 {% endif %}

{% endtest %}
```

- `model` và `column_name` được dbt tự truyền vào.
- Tham số khác (`allow_zero`) truyền từ YAML.

Dùng:

```yaml
models:
  - name: fct_sales
    columns:
      - name: line_total_amount
        data_tests:
          - is_positive
      - name: discount_amount
        data_tests:
          - is_positive:
              allow_zero: true
```

### Test ở mức model (không gắn cột)

```sql
-- tests/generic/test_date_order.sql
{% test date_order(model, start_column, end_column) %}

select *
from {{ model }}
where {{ end_column }} < {{ start_column }}

{% endtest %}
```

```yaml
models:
  - name: fct_sales
    data_tests:
      - date_order:
          start_column: order_date
          end_column: ship_date
```

## Cấu hình test

```yaml
data_tests:
  - is_positive:
      config:
        severity: error          # hoặc warn
        error_if: ">100"         # chỉ error khi > 100 dòng lỗi
        warn_if: ">0"
        where: "order_date >= '2013-01-01'"   # chỉ test 1 phần dữ liệu
        store_failures: true     # lưu các dòng lỗi vào bảng để điều tra
        tags: ['finance']
```

| Config | Dùng khi |
|---|---|
| `severity: warn` | Vấn đề cần biết nhưng không chặn pipeline |
| `error_if` / `warn_if` | Chấp nhận một mức lỗi nhỏ |
| `where` | Dữ liệu cũ bẩn không sửa được, chỉ test dữ liệu mới |
| `store_failures` | Debug: xem ngay dòng nào lỗi trong warehouse |

## Singular test — khi nào dùng

Khi kiểm tra quá đặc thù, không đáng tổng quát hoá:

```sql
-- tests/assert_sales_total_matches_source.sql
with mart as (select sum(line_total_amount) as total from {{ ref('fct_sales') }}),
     src  as (select sum(linetotal) as total from {{ source('sales', 'salesorderdetail') }})
select * from mart, src
where abs(mart.total - src.total) > 0.01
```

## Gợi ý custom generic test cho adventure_works

| Test | Kiểm tra |
|---|---|
| `is_positive(allow_zero)` | Số tiền, số lượng không âm |
| `date_order(start_column, end_column)` | `order_date ≤ ship_date ≤ due_date` |
| `one_current_row_per_key(key_column)` | Snapshot: mỗi khoá chỉ 1 dòng `dbt_valid_to is null` |
| ~~`no_overlapping_validity`~~ | Không cần tự viết: dùng `dbt_utils.mutually_exclusive_ranges` (xem [packages/01-dbt-utils.md](../tuan-1/packages/01-dbt-utils.md)) |
| `row_count_within_pct_of(compare_model, pct)` | Mart không lệch quá X% so với staging |

## Lỗi hay gặp

- Viết test trả về dòng **hợp lệ** thay vì dòng **vi phạm** (ngược logic).
- Test quá nhiều cột tầm thường, bỏ qua kiểm tra business quan trọng.
- Mọi test đều `severity: error` → pipeline gãy liên tục, cả team bắt đầu lờ test đi.
- Quên rằng `not_null` + `unique` ≠ primary key trên bảng ghép (cần `unique_combination_of_columns`).

## Áp dụng vào adventure_works

- [ ] ≥ 2 custom generic test trong `tests/generic/`, có tham số
- [ ] ≥ 1 singular test đối soát tổng với nguồn
- [ ] Phân loại severity hợp lý (error cho khoá, warn cho chất lượng mềm)
- [ ] Thử `store_failures: true` và xem bảng lỗi
- [ ] (Thêm) 1 unit test cho logic tính toán trong `fct_sales`

## Câu hỏi tự kiểm tra

1. Một test dbt "pass" khi nào?
2. Generic test và singular test khác nhau thế nào? Khi nào dùng loại nào?
3. `error_if: ">100"` nghĩa là gì?
4. Data test khác unit test thế nào?
5. Viết generic test kiểm tra một cột chỉ chứa chuỗi viết hoa.

## Tài liệu

- https://docs.getdbt.com/docs/build/data-tests
- https://docs.getdbt.com/best-practices/writing-custom-generic-tests
- https://docs.getdbt.com/reference/data-test-configs
- https://docs.getdbt.com/docs/build/unit-tests
