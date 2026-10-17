# dbt-utils — học sâu

> Ghi chú phiên bản: nội dung theo dbt-utils 1.x. Từ bản 1.0, các macro cross-database (`dateadd`, `datediff`, `concat`, `safe_cast`, `current_timestamp`...) **đã chuyển vào dbt Core**, gọi bằng `dbt.dateadd(...)` chứ không phải `dbt_utils.dateadd(...)`. Tài liệu/blog cũ vẫn ghi `dbt_utils.` → sẽ lỗi.

dbt-utils có 4 nhóm:

| Nhóm | Dùng ở | Ví dụ |
|---|---|---|
| A. SQL generators | Trong model | `generate_surrogate_key`, `star`, `date_spine`, `pivot` |
| B. Introspective macros | Trong model/macro, **query warehouse lúc compile** | `get_column_values`, `get_relations_by_pattern` |
| C. Generic tests | Trong YAML | `unique_combination_of_columns`, `accepted_range` |
| D. Jinja helpers | Trong macro | `log_info`, `pretty_time`, `slugify` |

---

## A. SQL generators

### `generate_surrogate_key(field_list)`

Tạo khoá thay thế bằng hash MD5 từ nhiều cột.

```sql
select
    {{ dbt_utils.generate_surrogate_key(['salesorderid', 'salesorderdetailid']) }} as sales_key,
    ...
```

Compile ra (đơn giản hoá):

```sql
md5(cast(
    coalesce(cast(salesorderid as varchar), '_dbt_utils_surrogate_key_null_')
    || '-' ||
    coalesce(cast(salesorderdetailid as varchar), '_dbt_utils_surrogate_key_null_')
as varchar)) as sales_key
```

Điểm cần hiểu:
- **Xử lý null:** null được thay bằng chuỗi đặc biệt → `(1, null)` và `(1, '')` cho ra 2 key khác nhau. Macro cũ `surrogate_key` (đã bỏ) coi null = chuỗi rỗng → có thể trùng key.
- **Dấu `-` ngăn cách** tránh trường hợp `('12', '3')` và `('1', '23')` cho cùng chuỗi `'123'`.
- **Thứ tự cột quan trọng:** `['a','b']` khác `['b','a']`. Dùng thống nhất ở fact và dim.
- Kết quả là chuỗi 32 ký tự hex. Join bằng chuỗi chậm hơn integer một chút, đổi lại không cần sequence, build song song được, tái tạo được.

### `star(from, relation_alias=False, except=[], prefix='', suffix='', quote_identifiers=True)`

Liệt kê tường minh mọi cột (thay `select *`), có thể bỏ cột, thêm tiền tố/hậu tố.

```sql
select
    {{ dbt_utils.star(from=ref('stg_sales__orders'), relation_alias='o', except=['modified_at']) }},
    {{ dbt_utils.star(from=ref('stg_sales__customers'), relation_alias='c', prefix='customer_', except=['customer_id']) }}
from {{ ref('stg_sales__orders') }} o
join {{ ref('stg_sales__customers') }} c using (customer_id)
```

- Là macro **introspective** (query danh sách cột lúc compile) → model upstream phải tồn tại trong warehouse.
- Upstream thêm cột → model tự có cột mới. Đây vừa là tiện lợi vừa là rủi ro (marts có contract sẽ báo lỗi → tốt).

### `date_spine(datepart, start_date, end_date)`

Sinh dãy thời gian liên tục — nền tảng của `dim_dates` và các bảng "mỗi ngày một dòng".

```sql
-- models/marts/core/dim_dates.sql
with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2011-01-01' as date)",
        end_date="cast('2015-01-01' as date)"
    ) }}
)
select
    cast(date_day as date)                         as date_day,
    extract(year from date_day)                    as year,
    extract(month from date_day)                   as month,
    extract(dayofweek from date_day)               as day_of_week   -- tên hàm tuỳ warehouse
from spine
```

- **`end_date` không bao gồm** (exclusive): ví dụ trên kết thúc ở 2014-12-31.
- Cột output tên `date_<datepart>` (`date_day`, `date_month`...).
- Muốn `dim_dates` giàu thuộc tính (quý, tuần ISO, ngày lễ, fiscal year) → xem package `dbt_date` (được cài kèm dbt-expectations).

Ứng dụng hay: **lấp ngày trống** khi vẽ chart doanh thu theo ngày:

```sql
select d.date_day, coalesce(sum(s.line_total_amount), 0) as revenue
from {{ ref('dim_dates') }} d
left join {{ ref('fct_sales') }} s on s.order_date = d.date_day
group by 1
```

### `union_relations(relations, exclude=[], include=[], column_override={}, source_column_name='_dbt_source_relation', where=none)`

Union nhiều bảng **khác cấu trúc**: cột thiếu tự điền `null`, thêm cột ghi nguồn gốc dòng.

```sql
{{ dbt_utils.union_relations(
    relations=[ref('stg_sales__orders_2012'), ref('stg_sales__orders_2013')],
    exclude=['_loaded_at']
) }}
```

Kết hợp với `get_relations_by_pattern` khi số bảng không cố định (xem nhóm B).

### `deduplicate(relation, partition_by, order_by)`

Giữ 1 dòng mỗi nhóm `partition_by`, chọn theo `order_by`.

```sql
{{ dbt_utils.deduplicate(
    relation=source('sales', 'salesorderheader'),
    partition_by='salesorderid',
    order_by='modifieddate desc'
) }}
```

Thực chất là `row_number() over (partition by ... order by ...) = 1`, nhưng viết đúng cú pháp tối ưu cho từng warehouse (vd `qualify` trên Snowflake/BigQuery). Rất hay dùng trong staging khi nguồn có bản ghi trùng, và để **dedupe batch trước khi `merge`** (tuần 2).

### `pivot(column, values, alias=True, agg='sum', cmp='=', prefix='', suffix='', then_value=1, else_value=0, quote_identifiers=True)`

Xoay dòng thành cột. Thường đi với `get_column_values` để lấy danh sách giá trị tự động.

```sql
select
    order_year,
    {{ dbt_utils.pivot(
        column='territory_name',
        values=dbt_utils.get_column_values(ref('dim_territories'), 'territory_name'),
        agg='sum',
        then_value='line_total_amount',
        else_value=0,
        prefix='revenue_'
    ) }}
from {{ ref('fct_sales') }}
group by 1
```

Compile ra một loạt `sum(case when territory_name = 'Northwest' then line_total_amount else 0 end) as revenue_northwest`...

### `unpivot(relation, cast_to='varchar', exclude=[], remove=[], field_name='field_name', value_name='value')`

Ngược với pivot: cột → dòng. Hữu ích khi nguồn có dạng "mỗi tháng một cột".

### Các macro nhỏ khác

| Macro | Làm gì | Ghi chú |
|---|---|---|
| `group_by(n)` | Sinh `group by 1, 2, ..., n` | Tiện khi có nhiều cột chiều |
| `generate_series(upper_bound)` | Dãy số 1..n | Dùng làm bảng số phụ trợ |
| `safe_add(field_list)` | Cộng nhiều cột, null coi như 0 | |
| `safe_subtract(field_list)` | Trừ, null coi như 0 | |
| `safe_divide(numerator, denominator)` | Chia, mẫu = 0 → `null` | ⚠️ Đã có sẵn → trong thư viện 5 macro tự viết, đừng viết lại `safe_divide`; chọn macro khác |
| `width_bucket(expr, min_value, max_value, num_buckets)` | Chia khoảng (histogram) | |
| `haversine_distance(lat1, lon1, lat2, lon2, unit)` | Khoảng cách địa lý | |
| `get_url_host/path/parameter` | Tách URL | Cho dữ liệu web analytics |

---

## B. Introspective macros — query warehouse lúc compile

Các macro này **chạy query thật trong lúc dbt compile**, rồi dùng kết quả để sinh SQL. Vì vậy:
- Bảng được query phải **đã tồn tại**.
- Lúc `dbt parse` (biến `execute = False`) chúng trả về giá trị mặc định → luôn truyền `default` hợp lý.
- Mỗi lần compile là 1 query → đừng lạm dụng trong project lớn.

| Macro | Trả về | Ví dụ dùng |
|---|---|---|
| `get_column_values(table, column, order_by='count(*) desc', max_records=none, default=[], where=none)` | List giá trị distinct | Danh sách cho `pivot`, sinh `case when` |
| `get_single_value(sql_statement, default=none)` | 1 giá trị | Lấy `max(order_date)` để dùng trong Jinja |
| `get_query_results_as_dict(sql_statement)` | Dict `{cột: [giá trị]}` | Sinh SQL từ bảng cấu hình (mapping) |
| `get_filtered_columns_in_relation(from, except=[])` | List tên cột | Tự viết logic giống `star` |
| `get_relations_by_pattern(schema_pattern, table_pattern, exclude='', database=target.database)` | List relation | Union mọi bảng `orders_20%` |
| `get_relations_by_prefix(schema, prefix, exclude='', database=target.database)` | List relation | Tương tự, theo tiền tố |

Ví dụ: union tất cả bảng theo năm mà không cần sửa code khi có năm mới:

```sql
{% set relations = dbt_utils.get_relations_by_pattern('sales_archive', 'orders_20%') %}
{{ dbt_utils.union_relations(relations=relations) }}
```

Ví dụ: sinh cột cờ từ bảng mapping:

```sql
{% set statuses = dbt_utils.get_column_values(ref('stg_sales__orders'), 'order_status', default=[]) %}
select
    order_id,
    {% for s in statuses %}
    order_status = {{ s }} as is_status_{{ s }}{{ "," if not loop.last }}
    {% endfor %}
from {{ ref('stg_sales__orders') }}
```

---

## C. Generic tests

Mọi test đều nhận thêm config chung (`severity`, `where`, `error_if`, `store_failures`...) như ở bài 2.4.

### Nhóm khoá & tính duy nhất

| Test | Kiểm tra | Tham số |
|---|---|---|
| `unique_combination_of_columns` | Tổ hợp cột là duy nhất (khoá ghép) | `combination_of_columns`, `quote_columns` |
| `not_constant` | Cột có ít nhất 2 giá trị khác nhau | `group_by_columns` |
| `cardinality_equality` | Số giá trị distinct của cột bằng cột ở bảng khác | `field`, `to` |

```yaml
models:
  - name: fct_sales
    data_tests:
      - dbt_utils.unique_combination_of_columns:
          combination_of_columns: [order_id, order_line_id]
```

### Nhóm giá trị

| Test | Kiểm tra | Tham số |
|---|---|---|
| `accepted_range` | Giá trị trong khoảng | `min_value`, `max_value`, `inclusive` |
| `expression_is_true` | Biểu thức SQL đúng với mọi dòng | `expression` |
| `not_accepted_values` | Không chứa giá trị cấm | `values` |
| `not_empty_string` | Không có chuỗi rỗng | `trim_whitespace` |
| `not_null_proportion` | Tỉ lệ không null ≥ ngưỡng | `at_least`, `at_most` |
| `at_least_one` | Có ít nhất 1 giá trị không null | |

`expression_is_true` dùng được ở 2 mức:

```yaml
models:
  - name: fct_sales
    data_tests:
      - dbt_utils.expression_is_true:          # mức model: viết đủ biểu thức
          expression: "total_due_amount >= subtotal_amount"
    columns:
      - name: unit_price
        data_tests:
          - dbt_utils.expression_is_true:      # mức cột: tên cột được ghép vào trước
              expression: ">= 0"
```

### Nhóm so sánh giữa 2 bảng (đối soát)

| Test | Kiểm tra | Tham số |
|---|---|---|
| `equal_rowcount` | 2 bảng cùng số dòng | `compare_model`, `group_by_columns` |
| `fewer_rows_than` | Ít dòng hơn bảng kia | `compare_model`, `group_by_columns` |
| `equality` | 2 bảng giống hệt nhau (từng dòng) | `compare_model`, `compare_columns`, `exclude_columns` |
| `relationships_where` | Như `relationships` nhưng có điều kiện lọc | `to`, `field`, `from_condition`, `to_condition` |

`equality` rất có giá trị ở tuần 2: **so model incremental với bản full refresh** để chứng minh logic đúng. Có thể so với một **seed** chứa kết quả mong đợi.

```yaml
models:
  - name: stg_sales__orders
    data_tests:
      - dbt_utils.equal_rowcount:
          compare_model: source('sales', 'salesorderheader')
```

### Nhóm thời gian & chuỗi

| Test | Kiểm tra | Tham số |
|---|---|---|
| `recency` | Có dữ liệu mới trong N đơn vị thời gian | `datepart`, `field`, `interval`, `group_by_columns` |
| `sequential_values` | Giá trị tăng liên tục, không nhảy cóc | `interval`, `datepart`, `group_by_columns` |
| `mutually_exclusive_ranges` | Các khoảng không chồng nhau (và có/không có khe hở) | `lower_bound_column`, `upper_bound_column`, `partition_by`, `gaps`, `zero_length_range_allowed` |

`mutually_exclusive_ranges` chính là test chuẩn cho **snapshot SCD2** (bài 2.3) — không cần tự viết `no_overlapping_validity`:

```yaml
snapshots:
  - name: snap_products
    data_tests:
      - dbt_utils.mutually_exclusive_ranges:
          lower_bound_column: dbt_valid_from
          upper_bound_column: coalesce(dbt_valid_to, cast('9999-12-31' as timestamp))
          partition_by: product_id
          gaps: not_allowed      # allowed | not_allowed | required
```

### `group_by_columns` — test theo nhóm

Một số test (`recency`, `equal_rowcount`, `fewer_rows_than`, `not_constant`, `at_least_one`, `sequential_values`, `not_null_proportion`) cho phép kiểm tra **từng nhóm**:

```yaml
- dbt_utils.recency:
    datepart: day
    field: order_date
    interval: 7
    group_by_columns: ['territory_id']   # mỗi territory đều phải có đơn trong 7 ngày
```

Thiếu tham số này, test chỉ biết "toàn bảng có dữ liệu mới" mà không phát hiện 1 territory bị mất dữ liệu.

---

## D. Jinja helpers (dùng khi viết macro)

| Macro | Dùng để |
|---|---|
| `log_info(message)` | In log có timestamp — debug macro, `run-operation` |
| `pretty_time(format)` | Thời gian hiện tại dạng đẹp |
| `pretty_log_format(message)` | Định dạng log giống dbt |
| `slugify(string)` | Chuỗi → dạng an toàn làm tên cột (`"North West"` → `north_west`) |

`slugify` hay đi cùng `pivot` khi giá trị có dấu cách hoặc ký tự đặc biệt.

---

## Lỗi hay gặp

- Gọi `dbt_utils.dateadd`, `dbt_utils.datediff`... → đã chuyển sang `dbt.dateadd`.
- Dùng `surrogate_key` (cũ) → lỗi/deprecation, đổi sang `generate_surrogate_key`.
- `star`/`get_column_values` trên model chưa build → lỗi "relation does not exist" ở lần chạy đầu tiên của môi trường mới (CI!). Cách giảm: truyền `default`, hoặc dùng `--defer` để trỏ sang prod.
- `date_spine` thiếu ngày cuối vì quên `end_date` là exclusive.
- `expression_is_true` mức cột nhưng viết cả tên cột → biểu thức thành `unit_price unit_price >= 0`.

## Bài tập trên adventure_works

- [ ] `generate_surrogate_key` cho `fct_sales`, `dim_customers`, `dim_products`; giải thích null-handling trong README
- [ ] `dim_dates` từ `date_spine` (2011-01-01 → 2015-01-01)
- [ ] `deduplicate` trong ít nhất 1 model staging
- [ ] `star` với `except` + `prefix` khi join trong intermediate
- [ ] `pivot` + `get_column_values`: doanh thu theo năm × territory
- [ ] Test: `unique_combination_of_columns`, `accepted_range`, `expression_is_true`, `equal_rowcount` (stg vs source), `mutually_exclusive_ranges` (snapshot), `recency` có `group_by_columns`
- [ ] Mở `dbt_packages/dbt_utils/macros/sql/generate_surrogate_key.sql` và `deduplicate.sql`, đọc hiểu `adapter.dispatch`

## Câu hỏi tự kiểm tra

1. Vì sao `generate_surrogate_key` dùng dấu `-` ngăn cách và thay null bằng chuỗi đặc biệt?
2. Macro introspective là gì? Rủi ro khi chạy trong CI trên schema mới?
3. `date_spine` với `end_date='2015-01-01'` có chứa ngày 2015-01-01 không?
4. Test nào kiểm tra snapshot không có khoảng hiệu lực chồng nhau?
5. `recency` có và không có `group_by_columns` khác nhau thế nào?
6. Vì sao `dbt_utils.dateadd` báo lỗi ở dbt-utils 1.x?
