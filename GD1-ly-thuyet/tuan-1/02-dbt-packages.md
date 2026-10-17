# 1.2 dbt packages: dbt-utils, codegen, dbt-expectations

> File này là tổng quan. Học sâu từng package: [packages/](packages/README.md).

## Khái niệm

Package là một dbt project khác (macro, test, đôi khi model) được cài vào project của bạn. Giống `pip install` cho dbt.

```yaml
# packages.yml  (dbt ≥ 1.6 cũng chấp nhận dependencies.yml)
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.1.0", "<2.0.0"]
  - package: dbt-labs/codegen
    version: [">=0.12.0", "<1.0.0"]
  - package: metaplane/dbt_expectations
    version: [">=0.10.0", "<0.11.0"]
```

```bash
dbt deps    # tải về thư mục dbt_packages/ và tạo package-lock.yml
```

- **Luôn ghim khoảng version** để tránh build gãy khi package ra bản mới.
- Commit `package-lock.yml`, **không** commit `dbt_packages/` (thêm vào `.gitignore`).
- Kiểm tra version mới nhất và tương thích dbt tại https://hub.getdbt.com trước khi ghim.
- Ghi chú: `dbt-expectations` bản gốc của Calogica đã ngừng phát triển (cuối 2024); bản tiếp tục được duy trì là của **Metaplane**. Nếu tài liệu cũ ghi `calogica/dbt_expectations` thì đó là bản cũ.

Gọi macro của package: `{{ <tên_package>.<tên_macro>(...) }}`, ví dụ `{{ dbt_utils.star(...) }}`.

---

## dbt-utils — "thư viện chuẩn" của dbt

### Macro SQL hay dùng

| Macro | Dùng để | Ví dụ |
|---|---|---|
| `generate_surrogate_key` | Tạo khoá thay thế (hash) từ nhiều cột | `{{ dbt_utils.generate_surrogate_key(['order_id', 'order_line_id']) }} as sales_key` |
| `star` | `select *` trừ vài cột | `{{ dbt_utils.star(ref('stg_sales__orders'), except=['modified_at']) }}` |
| `date_spine` | Sinh dãy ngày liên tục → làm `dim_dates` | xem dưới |
| `union_relations` | Union nhiều bảng khác cột, tự điền null | gộp bảng theo năm |
| `deduplicate` | Bỏ trùng theo partition + order | lấy bản ghi mới nhất |
| `pivot` + `get_column_values` | Pivot động theo giá trị cột | doanh thu theo territory |

```sql
-- models/marts/core/dim_dates.sql
{{ dbt_utils.date_spine(
    datepart="day",
    start_date="cast('2011-01-01' as date)",
    end_date="cast('2015-01-01' as date)"
) }}
```

### Generic test có sẵn

| Test | Kiểm tra |
|---|---|
| `unique_combination_of_columns` | Khoá ghép duy nhất (rất cần cho fact) |
| `expression_is_true` | Biểu thức đúng với mọi dòng, vd `total_due_amount >= subtotal_amount` |
| `accepted_range` | Giá trị nằm trong khoảng |
| `recency` | Bảng có dữ liệu mới trong N ngày |
| `equal_rowcount` / `fewer_rows_than` | So số dòng giữa 2 model |
| `not_null_proportion` | Tỉ lệ không null ≥ ngưỡng |

```yaml
models:
  - name: fct_sales
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns: [order_id, order_line_id]
    columns:
      - name: line_total_amount
        data_tests:
          - dbt_utils.accepted_range:
              min_value: 0
```

---

## codegen — sinh code boilerplate

Không dùng trong model; chạy bằng `dbt run-operation` để **in ra YAML/SQL** rồi copy vào file.

| Macro | Sinh ra |
|---|---|
| `generate_source` | Khối `sources:` từ schema trong warehouse |
| `generate_base_model` | SQL model staging (CTE `source` + `renamed`) |
| `generate_model_yaml` | YAML khai báo cột cho model đã có |
| `generate_model_import_ctes` | Đổi `ref`/`source` trong SQL thành import CTE đầu file |

```bash
dbt run-operation generate_source \
  --args '{"schema_name": "sales", "database_name": "adventure_works", "generate_columns": true}'

dbt run-operation generate_base_model \
  --args '{"source_name": "sales", "table_name": "salesorderheader"}'

dbt run-operation generate_model_yaml \
  --args '{"model_names": ["stg_sales__orders"]}'
```

Ý nghĩa: tiết kiệm thời gian gõ tay và giảm lỗi chính tả tên cột. Output vẫn cần bạn **sửa lại** (rename, cast, viết description).

---

## dbt-expectations — test kiểu Great Expectations

Bổ sung các test về **phân phối, định dạng, khoảng giá trị, độ tươi**, mà test mặc định của dbt (`unique`, `not_null`, `accepted_values`, `relationships`) không có.

| Test | Ví dụ dùng |
|---|---|
| `expect_column_values_to_be_between` | `unit_price` trong [0, 10000] |
| `expect_column_values_to_match_regex` | email đúng định dạng |
| `expect_table_row_count_to_be_between` | bảng không bỗng nhiên rỗng |
| `expect_row_values_to_have_recent_data` | có dữ liệu trong 1 ngày gần nhất |
| `expect_column_pair_values_A_to_be_greater_than_B` | `due_date >= order_date` |
| `expect_compound_columns_to_be_unique` | khoá ghép duy nhất |

```yaml
columns:
  - name: email_address
    data_tests:
      - dbt_expectations.expect_column_values_to_match_regex:
          regex: "^[^@]+@[^@]+\\.[^@]+$"
          row_condition: "email_address is not null"
```

Lưu ý: package này kéo theo `dbt_date` như dependency; regex flavor phụ thuộc warehouse.

---

## Lỗi hay gặp

- Không ghim version → CI một ngày tự gãy.
- Commit `dbt_packages/` vào git.
- Cài package nhưng không dùng → "cài cho có" trong portfolio, reviewer nhận ra ngay.
- Dùng `generate_surrogate_key` rồi lại join bằng natural key → khoá thay thế vô nghĩa.

## Áp dụng vào adventure_works

- [ ] `packages.yml` ghim version, `dbt deps` chạy được, `package-lock.yml` được commit
- [ ] Dùng codegen sinh sources + base model cho ít nhất 1 schema
- [ ] `generate_surrogate_key` cho khoá của fact/dim
- [ ] `dim_dates` từ `date_spine`
- [ ] ≥ 3 test của dbt-utils, ≥ 3 test của dbt-expectations

## Câu hỏi tự kiểm tra

1. `dbt deps` tải package về đâu? File nào cần commit?
2. Khác nhau giữa macro dùng trong model (`dbt_utils.star`) và macro dùng qua `run-operation` (codegen)?
3. Tại sao surrogate key dạng hash lại hữu ích khi khoá tự nhiên là khoá ghép?
4. Kể 2 kiểm tra mà test mặc định của dbt không làm được nhưng dbt-expectations làm được.

## Tài liệu

- https://docs.getdbt.com/docs/build/packages
- https://hub.getdbt.com/dbt-labs/dbt_utils/latest/
- https://hub.getdbt.com/dbt-labs/codegen/latest/
- https://github.com/metaplane/dbt-expectations
