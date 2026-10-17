# 02 — Jinja (J1–J10)

> Lý thuyết: [GD1-ly-thuyet/tuan-1/03-jinja-va-macro.md](../../GD1-ly-thuyet/tuan-1/03-jinja-va-macro.md)
>
> Thói quen bắt buộc: sau mỗi thay đổi, chạy `dbt compile -s <model>` và mở file trong `target/compiled/lab/...` để xem SQL thật. Jinja sai thường vẫn compile được, nhưng ra SQL lạ.

Làm sau [01-co-ban.md](01-co-ban.md): J1–J2 refactor chính staging bạn đã viết ở B3/B4. J1–J6 làm ở **ngày 0** là được. J7, J9, J10 gắn với bài incremental/SCD2.

---

## J1 ⭐ Macro `cents_to_dollars`

**Bối cảnh:** staging bạn viết ở B3/B4 đang lặp cùng một phép đổi cents → dollars ở 3 model. Ngoài thực tế, mỗi người viết một kiểu (`/100`, `/100.0`, `round` hoặc không) là nguồn gốc của các con số lệch nhau vài cent giữa các báo cáo.

**Yêu cầu**
- Tạo `macros/cents_to_dollars.sql` chứa macro `cents_to_dollars(column_name, scale=2)`.
- Thay phép chia ở `stg_products`, `stg_orders`, `stg_order_items` bằng macro.

**Kiểm tra:** `dbt build -s staging` rồi `python scripts/check.py J1`.

**Câu hỏi suy ngẫm**
1. Vì sao chia cho `100.0` chứ không phải `100`? (Thử nghĩ trên Postgres: `199 / 100` ra bao nhiêu?)
2. Gọi `{{ cents_to_dollars('amount_cents', 0) }}` và `{{ cents_to_dollars('amount_cents', scale=0) }}` khác gì nhau?

<details><summary>Gợi ý</summary>

```sql
{% macro cents_to_dollars(column_name, scale=2) -%}
    round({{ column_name }} / 100.0, {{ scale }})
{%- endmacro %}
```
Lưu ý `-` trong `{%-` và `-%}` để không sinh khoảng trắng/xuống dòng thừa.
</details>

---

## J2 ⭐⭐ Macro `clean_string`

**Bối cảnh:** `raw.products` có tên `"  Basic T-Shirt "`, category `''`; email khách 2 là `"  Binh.Tran@Mail.com "`.

**Yêu cầu**
- `clean_string(column_name, lower=false)`: `trim`, nếu `lower=true` thì thêm `lower`, cuối cùng chuỗi rỗng → `null`.
- Dùng trong `stg_customers`, `stg_customer_changelog`, `stg_products` (email dùng `lower=true`).

**Kiểm tra:** `check.py J2`.

**Câu hỏi suy ngẫm**
1. Bạn ghép chuỗi bằng `~` hay `+` trong Jinja? Khác nhau thế nào?
2. Mở SQL compiled: có dòng trống thừa không? Sửa bằng whitespace control.

<details><summary>Gợi ý</summary>

Dựng biểu thức dần bằng `{% set expr = 'trim(' ~ column_name ~ ')' %}`, rồi `{% if lower %}{% set expr = 'lower(' ~ expr ~ ')' %}{% endif %}`, cuối cùng `nullif({{ expr }}, '')`.
</details>

---

## J3 ⭐⭐ Pivot bằng `for` + `var`

**Yêu cầu:** model `models/marts/customer_order_summary.sql`, 1 dòng mỗi khách:

| Cột | Ý nghĩa |
|---|---|
| `customer_id` | |
| `total_orders` | tổng số đơn |
| `orders_placed`, `orders_shipped`, `orders_delivered`, `orders_cancelled` | số đơn theo trạng thái |

Danh sách trạng thái lấy từ `var('order_statuses')` (đã khai trong `dbt_project.yml`). **Không** viết tay 4 cột.

**Kiểm tra:** `check.py J3`.

**Câu hỏi suy ngẫm**
1. Bỏ `loop.last` thì SQL compiled bị lỗi gì?
2. Nếu ngày mai có trạng thái `returned`, bạn phải sửa ở đâu? Có cách nào không phải sửa không? (→ J4)

<details><summary>Gợi ý</summary>

```sql
{%- for s in var('order_statuses') %}
    sum(case when order_status = '{{ s }}' then 1 else 0 end) as orders_{{ s }}
    {{- "," if not loop.last }}
{%- endfor %}
```
</details>

---

## J4 ⭐⭐⭐ Pivot động bằng `run_query`

**Yêu cầu**
- Macro `get_order_statuses()` chạy `select distinct order_status from {{ ref('stg_orders') }}` bằng `run_query`, trả về list.
- Model `customer_order_summary_dynamic.sql` giống J3, nhưng danh sách trạng thái lấy từ macro.

**Kiểm tra:** `check.py J4` ở ngày 0, rồi sang **ngày 4** (có đơn bị huỷ) build lại và kiểm tra lần nữa.

**Quan sát:** ở ngày 0 model **không có** cột `orders_cancelled`; từ ngày 4 cột này mới xuất hiện.

**Thử nghiệm `depends_on`:** model của bạn chạy được vì thân model đã có `from {{ ref('stg_orders') }}`. Giờ tạo model tạm `tmp_dep_test.sql` gọi `get_order_statuses()` nhưng chỉ đọc `from {{ ref('fct_events') }}`, rồi build. dbt sẽ báo *"dbt was unable to infer all dependencies for the model"* và gợi ý thêm `-- depends_on: {{ ref('stg_orders') }}`. Thêm dòng đó vào đầu model → hết lỗi. Xoá model tạm sau khi thử.

**Câu hỏi suy ngẫm**
1. Vì sao phải bọc `run_query` trong `{% if execute %}`? Lúc parse thì macro trả về gì?
2. Vì sao `ref()` nằm trong nhánh `execute` thì dbt không "thấy" phụ thuộc lúc parse?
3. Schema model thay đổi theo dữ liệu: điều này nguy hiểm thế nào với dashboard, với model contract?
4. So sánh với `dbt_utils.get_column_values(ref('stg_orders'), 'order_status')`: ở đây `ref()` được gọi ngay trong model (ngoài nhánh `execute`), nên dbt luôn thấy phụ thuộc.

<details><summary>Gợi ý</summary>

```sql
{% macro get_order_statuses() %}
    {% if execute %}
        {% set rows = run_query("select distinct order_status from " ~ ref('stg_orders') ~ " order by 1") %}
        {{ return(rows.columns[0].values() | list) }}
    {% else %}
        {{ return([]) }}
    {% endif %}
{% endmacro %}
```
`ref()` nằm trong nhánh `execute` nên lúc parse dbt không thấy nó. Nếu thân model không tự `ref` tới model đó thì phải khai `-- depends_on` ở đầu model.
</details>

---

## J5 ⭐⭐⭐ Custom generic test

**Yêu cầu:** trong `tests/generic/`:

| Test | Tham số | Fail khi |
|---|---|---|
| `is_positive` | `allow_zero=false` | giá trị `<= 0` (hoặc `< 0` nếu `allow_zero`) |
| `one_current_row_per_key` | `current_condition='dbt_valid_to is null'` | một khoá có > 1 dòng thoả `current_condition` |

Gắn vào YAML (dùng `arguments:` — xem 00-setup mục 5):
- `is_positive` cho `fct_orders.amount`, và `allow_zero: true` cho `fct_daily_revenue.revenue` (làm khi tới bài I3/I5).
- `one_current_row_per_key` cho snapshot và các dim SCD2 (bài S2, S5, S7, S8).

**Kiểm tra:** `check.py J5`. Thử cố ý làm test fail (vd đổi điều kiện), chạy `dbt test -s <model> --store-failures`, rồi `dbt show` bảng lỗi.

**Câu hỏi suy ngẫm:** Test generic trả về gì thì được coi là pass?

<details><summary>Gợi ý</summary>

```sql
{% test one_current_row_per_key(model, column_name, current_condition='dbt_valid_to is null') %}
select {{ column_name }}, count(*) as n_current
from {{ model }}
where {{ current_condition }}
group by {{ column_name }}
having count(*) > 1
{% endtest %}
```
</details>

---

## J6 ⭐⭐⭐ `generate_schema_name`

**Yêu cầu**
1. Trong `dbt_project.yml`, cho marts vào custom schema: thêm `+schema: marts` dưới `marts:`.
2. Build và xem schema được tạo: mặc định dbt đặt `dev_marts`.
3. Override `generate_schema_name` sao cho:
   - target `dev`: `dev_marts` (giữ nguyên, để mỗi dev có schema riêng)
   - target `prod`: đúng `marts`
   - model không có custom schema: dùng `target.schema`
4. `dbt run --target prod -s staging customer_order_summary` (dùng `run` để không kéo theo test của các model chưa có ở prod), rồi kiểm tra:
   ```bash
   dbt show --inline "select distinct table_schema from information_schema.tables order by 1"
   ```

**Kiểm tra:** `check.py J6` (chỉ kiểm tra có macro; phần schema bạn tự kiểm bằng lệnh trên).

**Câu hỏi suy ngẫm:** Vì sao dbt mặc định *nối* tên schema thay vì dùng thẳng custom schema?

---

## J7 ⭐⭐⭐ Macro `get_incremental_filter` → dùng ở bài I6

**Yêu cầu:** `get_incremental_filter(column_name, lookback_days=none)`:
- Khi model **không** ở chế độ incremental: không sinh ra gì.
- Khi incremental: sinh `where <col> >= max(<col>) trong {{ this }} − N ngày`.
- `N` mặc định lấy từ `var('lookback_days')`.
- Dùng `dbt.dateadd(...)` thay vì viết `interval` cứng (để chạy được trên warehouse khác).

**Kiểm tra:** làm cùng bài I6. `dbt compile -s fct_events_by_ts` trước và sau khi bảng tồn tại, so 2 file compiled.

<details><summary>Gợi ý</summary>

`is_incremental()` gọi được bên trong macro. `dbt.dateadd('day', -1 * days, 'max(' ~ column_name ~ ')')`.
</details>

---

## J8 ⭐⭐⭐⭐ Audit project bằng `graph`

**Yêu cầu:** macro `audit_incremental_models()` chạy bằng:

```bash
dbt run-operation audit_incremental_models
```

- In ra bảng: tên model | strategy | unique_key | on_schema_change, cho mọi model incremental **của project** (bỏ qua package).
- Nếu có model dùng `merge` hoặc `delete+insert` mà **thiếu `unique_key`** → raise compiler error (lệnh trả exit code ≠ 0, dùng được trong CI).

**Kiểm tra:** `check.py J8`, rồi tạm xoá `unique_key` ở một model để thấy lỗi.

**Câu hỏi suy ngẫm:** Ngoài check này, bạn sẽ thêm quy tắc nào nữa cho project? (gợi ý: model incremental bắt buộc có `on_schema_change` khác `ignore`)

<details><summary>Gợi ý</summary>

`graph.nodes.values() | selectattr('resource_type', 'equalto', 'model') | selectattr('package_name', 'equalto', project_name)`; đọc `node.config.materialized`, `node.config.incremental_strategy`, `node.config.unique_key`; in bằng `{{ print(...) }}`; báo lỗi bằng `{{ exceptions.raise_compiler_error('...') }}`. Bọc tất cả trong `{% if execute %}`.
</details>

---

## J9 ⭐⭐⭐⭐ `adapter.dispatch`

**Yêu cầu**
- Macro `days_between(start_date, end_date)` gọi `adapter.dispatch('days_between')(...)`.
- `default__days_between`: dùng `dbt.datediff`.
- `duckdb__days_between`: dùng hàm riêng của DuckDB `date_diff('day', ...)`.
- Dùng trong `fct_orders`: cột `days_to_last_update = days_between(order_date, updated_at)`.

**Kiểm tra:** `check.py J9`. Mở SQL compiled của `fct_orders`: thấy bản `duckdb__` được chọn.

**Câu hỏi suy ngẫm:** dbt tìm macro theo thứ tự nào (`duckdb__`, `postgres__`, `default__`...)? Đây chính là cách dbt-utils chạy được trên mọi warehouse.

---

## J10 ⭐⭐⭐⭐ Macro `scd2_from_changelog` → làm ở bài S8

Macro sinh **cả một model SCD2** từ bảng CDC log. Đề chi tiết ở [04-snapshot-scd2.md — S8](04-snapshot-scd2.md#s8-scd2-từ-cdc-log).

---

## Bonus (gắn với I7): introspection

Ở bài I7, bạn sẽ cần `stg_orders` **chỉ** chọn cột `channel` khi nguồn đã có cột này. Dùng:

```sql
{%- set cols = adapter.get_columns_in_relation(source('raw', 'orders')) | map(attribute='name') | list -%}
```
