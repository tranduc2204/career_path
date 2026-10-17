# 1.3 Jinja và macro — xây thư viện 5 macro

## Khái niệm

**Jinja** là ngôn ngữ template (Python). dbt chạy Jinja trước để **render ra SQL thuần**, rồi mới gửi SQL đó cho warehouse. Bạn có thể xem SQL đã render trong `target/compiled/`.

```
model.sql (SQL + Jinja) ──dbt compile──▶ target/compiled/.../model.sql (SQL thuần) ──▶ warehouse
```

3 loại cú pháp:

| Cú pháp | Ý nghĩa | Ví dụ |
|---|---|---|
| `{{ ... }}` | Biểu thức, in ra kết quả | `{{ ref('stg_sales__orders') }}` |
| `{% ... %}` | Câu lệnh: `if`, `for`, `set`, `macro` | `{% for m in methods %}` |
| `{# ... #}` | Comment, không xuất hiện trong SQL | `{# TODO #}` |

**Macro** = hàm Jinja tái sử dụng, đặt trong thư mục `macros/`.

```sql
-- macros/cents_to_dollars.sql
{% macro cents_to_dollars(column_name, scale=2) %}
    round(cast({{ column_name }} as numeric) / 100, {{ scale }})
{% endmacro %}
```

```sql
select {{ cents_to_dollars('amount_cents') }} as amount_usd from ...
```

## Các thứ cần biết

### Biến và đối tượng có sẵn

| Đối tượng | Dùng để |
|---|---|
| `target.name`, `target.schema` | Biết đang chạy dev hay prod |
| `this` | Relation của chính model đang build (dùng nhiều trong incremental) |
| `var('ten')` | Biến truyền từ `dbt_project.yml` hoặc `--vars` |
| `env_var('TEN')` | Biến môi trường (secrets, cấu hình CI) |
| `config.get(...)` | Đọc config của model |
| `execute` | `False` lúc parse, `True` lúc chạy thật — dùng để tránh query lúc parse |

### Whitespace control

`{%- ... -%}` xoá khoảng trắng/xuống dòng thừa, giúp SQL compile gọn.

### Macro chạy query: `run_query`

```sql
{% macro get_order_statuses() %}
    {% set q %} select distinct order_status from {{ ref('stg_sales__orders') }} {% endset %}
    {% if execute %}
        {% set results = run_query(q) %}
        {{ return(results.columns[0].values()) }}
    {% else %}
        {{ return([]) }}
    {% endif %}
{% endmacro %}
```

### `run-operation`

Gọi macro trực tiếp từ CLI, không qua model (dùng cho tác vụ quản trị: grant, dọn schema...):

```bash
dbt run-operation drop_ci_schemas --args '{"prefix": "dbt_ci_"}'
```

### Ghi đè macro có sẵn của dbt: `generate_schema_name`

Mặc định dbt tạo schema `<target_schema>_<custom_schema>` (vd `dbt_dustin_marts`). Muốn **prod dùng đúng `marts`**, dev vẫn dùng schema riêng:

```sql
-- macros/generate_schema_name.sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if target.name == 'prod' and custom_schema_name is not none -%}
        {{ custom_schema_name | trim }}
    {%- elif custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

### Dispatch (biết để đọc code package)

`adapter.dispatch` cho phép 1 macro có nhiều bản cài đặt theo warehouse (`snowflake__x`, `bigquery__x`, `default__x`). Đây là cách dbt-utils chạy được trên mọi warehouse.

## Gợi ý thư viện 5 macro cho adventure_works

Chọn macro **giải quyết vấn đề thật** của project, không chọn vì "cho đủ số".

| # | Macro | Vấn đề giải quyết | Ghi chú |
|---|---|---|---|
| 1 | `generate_schema_name` (override) | Tách schema dev/prod | Bắt buộc gần như mọi project thật |
| 2 | `limit_data_in_dev(column, days)` | Dev chạy nhanh, chỉ lấy N ngày gần nhất | Dùng `target.name` |
| 3 | `get_incremental_filter(column, lookback_days)` | Filter incremental có lookback dùng chung (tuần 2) | Không dùng `safe_divide` vì dbt-utils đã có sẵn |
| 4 | `audit_columns()` | Thêm `_loaded_at`, `_dbt_invocation_id` vào marts | Dùng `run_started_at`, `invocation_id` |
| 5 | `clean_string(column)` | Chuẩn hoá chuỗi: trim, chuỗi rỗng → null | Dùng ở staging |

Phương án thay thế: `money(column)` cast tiền tệ thống nhất, `grant_select(role)` cho post-hook.

> Trước khi viết macro, kiểm tra dbt-utils đã có chưa (vd `safe_divide`, `safe_add`, `deduplicate`, `star`). Tự viết lại cái package đã có là điểm trừ khi review portfolio.

Ví dụ #2:

```sql
-- macros/limit_data_in_dev.sql
{% macro limit_data_in_dev(column_name, dev_days_of_data=90) %}
    {% if target.name == 'dev' %}
        where {{ column_name }} >= {{ dbt.dateadd('day', -1 * dev_days_of_data, dbt.current_timestamp()) }}
    {% endif %}
{% endmacro %}
```

`dbt.dateadd`, `dbt.current_timestamp` là cross-database macro có sẵn trong dbt Core → chạy được trên nhiều warehouse.

### Docs cho macro

```yaml
# macros/_macros.yml
macros:
  - name: safe_divide
    description: Chia an toàn, trả về null khi mẫu số bằng 0 hoặc null.
    arguments:
      - name: numerator
        type: string
        description: Cột hoặc biểu thức tử số
      - name: denominator
        type: string
        description: Cột hoặc biểu thức mẫu số
```

## Lỗi hay gặp

- Viết macro cho logic chỉ dùng 1 lần → khó đọc hơn SQL thường. Quy tắc: lặp lại ≥ 2–3 lần mới tách macro.
- Quên `{% if execute %}` khi `run_query` → lỗi hoặc query thừa lúc parse.
- Nhầm `{{ }}` và `{% %}`.
- Không xem `target/compiled/` khi debug.
- Hard-code tên schema/database trong macro.

## Áp dụng vào adventure_works

- [ ] 5 macro trong `macros/`, mỗi macro được dùng ở ≥ 1 model
- [ ] `_macros.yml` có description + arguments
- [ ] README có bảng "macro – vấn đề – ví dụ dùng"
- [ ] Mở `target/compiled/` kiểm tra SQL render đúng

## Câu hỏi tự kiểm tra

1. dbt render Jinja lúc nào, warehouse có thấy Jinja không?
2. Biến `execute` dùng để làm gì?
3. Mặc định dbt đặt tên schema thế nào khi có `+schema: marts`? Làm sao đổi?
4. `adapter.dispatch` giải quyết vấn đề gì?
5. Khi nào **không** nên viết macro?

## Tài liệu

- https://docs.getdbt.com/docs/build/jinja-macros
- https://docs.getdbt.com/docs/build/custom-schemas
- https://docs.getdbt.com/reference/dbt-jinja-functions
- Khoá dbt Learn: *Jinja, Macros, and Packages*
