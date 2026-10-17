# dbt-expectations — học sâu

## Bối cảnh

**Great Expectations** là framework kiểm tra chất lượng dữ liệu bằng Python, đặt tên test theo dạng câu "expect ... to ...". dbt-expectations mang bộ test đó **vào dbt dưới dạng generic test SQL** — không cần Python, chạy ngay trong `dbt test`.

- Bản gốc của Calogica (`calogica/dbt_expectations`) đã ngừng phát triển cuối 2024; bản được duy trì tiếp là **Metaplane** (`metaplane/dbt_expectations`). Tên test giữ nguyên, nên tài liệu cũ vẫn dùng được.
- Package kéo theo **`dbt_date`** làm dependency.

## Cài đặt

```yaml
# packages.yml
packages:
  - package: metaplane/dbt_expectations
    version: [">=0.10.0", "<0.11.0"]   # kiểm tra version mới nhất trên hub.getdbt.com
```

```yaml
# dbt_project.yml — bắt buộc cho các test liên quan thời gian
vars:
  'dbt_date:time_zone': 'Asia/Ho_Chi_Minh'
```

## Tham số dùng chung (gặp ở nhiều test)

| Tham số | Ý nghĩa |
|---|---|
| `row_condition` | Chỉ test các dòng thoả điều kiện, vd `"order_status = 5"` |
| `strictly` | `true` → so sánh chặt (`<` thay `<=`) |
| `group_by` | Kiểm tra theo từng nhóm |
| `quote_columns` / `quote_values` | Bọc tên cột/giá trị bằng nháy |

`row_condition` khác config `where` thế nào? Gần như cùng tác dụng (lọc trước khi test). `where` là config chung của dbt cho mọi test; `row_condition` là tham số riêng của dbt-expectations. Dùng cái nào cũng được, nên thống nhất trong project.

---

## Bản đồ các nhóm test

```
dbt-expectations
├── 1. Table shape        — bảng có đúng cột? đủ dòng? dữ liệu có mới?
├── 2. Null/unique/type   — từng cột: null, trùng, kiểu dữ liệu
├── 3. Sets & ranges      — giá trị thuộc tập, trong khoảng, tăng/giảm dần
├── 4. String matching    — độ dài, LIKE, regex
├── 5. Aggregate          — min/max/mean/sum/distinct count của cột trong khoảng
├── 6. Multi-column       — quan hệ giữa các cột (A > B, tổng các cột = X)
└── 7. Distributional     — phát hiện bất thường theo độ lệch chuẩn, đủ dữ liệu mỗi ngày
```

---

### 1. Table shape

| Test | Kiểm tra |
|---|---|
| `expect_table_row_count_to_be_between` | Số dòng trong [min, max] — bắt bảng **đột nhiên rỗng** |
| `expect_table_row_count_to_equal` | Số dòng = N |
| `expect_table_row_count_to_equal_other_table` | Bằng số dòng bảng khác |
| `expect_table_row_count_to_equal_other_table_times_factor` | = bảng khác × hệ số (vd fact line ≈ 2.5 × header) |
| `expect_table_column_count_to_be_between` / `_to_equal` | Số cột |
| `expect_table_columns_to_match_set` | Đúng tập cột (không quan tâm thứ tự) |
| `expect_table_columns_to_match_ordered_list` | Đúng tập cột theo thứ tự |
| `expect_table_columns_to_contain_set` / `_not_contain_set` | Có / không có các cột |
| `expect_column_to_exist` | Cột tồn tại |
| `expect_row_values_to_have_recent_data` | Có dữ liệu mới trong N `datepart` |
| `expect_grouped_row_values_to_have_recent_data` | Như trên nhưng **từng nhóm** |
| `expect_table_aggregation_to_equal_other_table` | Một phép tổng hợp khớp với bảng khác (đối soát) |

```yaml
models:
  - name: fct_sales
    data_tests:
      - dbt_expectations.expect_table_row_count_to_be_between:
          min_value: 100000
      - dbt_expectations.expect_table_aggregation_to_equal_other_table:
          expression: sum(line_total_amount)
          compare_model: source('sales', 'salesorderdetail')
          compare_expression: sum(linetotal)
          tolerance_percent: 0.001
    columns:
      - name: order_date
        data_tests:
          - dbt_expectations.expect_row_values_to_have_recent_data:
              datepart: day
              interval: 1
```

> AdventureWorks dừng ở 2014 → test "recent data" sẽ fail. Dùng `severity: warn` hoặc chỉ minh hoạ, giống vấn đề freshness ở bài 3.6.

### 2. Null, unique, kiểu dữ liệu

| Test | Kiểm tra |
|---|---|
| `expect_column_values_to_not_be_null` / `_to_be_null` | Null (có `row_condition` → hơn `not_null` mặc định) |
| `expect_column_values_to_be_unique` | Duy nhất |
| `expect_column_values_to_be_of_type` | Kiểu dữ liệu đúng |
| `expect_column_values_to_be_in_type_list` | Kiểu thuộc danh sách |
| `expect_column_values_to_have_consistent_casing` | Hoa/thường nhất quán |

```yaml
- name: ship_date
  data_tests:
    - dbt_expectations.expect_column_values_to_not_be_null:
        row_condition: "order_status = 5"   # chỉ đơn đã giao mới bắt buộc có ship_date
```

Đây là ví dụ kinh điển cho thấy giá trị của `row_condition`: `not_null` mặc định không diễn tả được "không null **khi** ...".

### 3. Sets & ranges

| Test | Kiểm tra |
|---|---|
| `expect_column_values_to_be_between` | Từng giá trị trong [min, max] |
| `expect_column_values_to_be_in_set` / `_not_be_in_set` | Thuộc / không thuộc tập |
| `expect_column_values_to_be_increasing` / `_decreasing` | Tăng/giảm dần (theo `sort_column`, `group_by`) |

```yaml
- name: unit_price_discount
  data_tests:
    - dbt_expectations.expect_column_values_to_be_between:
        min_value: 0
        max_value: 1
- name: order_status
  data_tests:
    - dbt_expectations.expect_column_values_to_be_in_set:
        value_set: [1, 2, 3, 4, 5, 6]
```

### 4. String matching

| Test | Kiểm tra |
|---|---|
| `expect_column_value_lengths_to_be_between` / `_to_equal` | Độ dài chuỗi |
| `expect_column_values_to_match_like_pattern` / `_not_match_like_pattern` | Khớp `LIKE` |
| `expect_column_values_to_match_like_pattern_list` | Khớp 1 trong nhiều pattern |
| `expect_column_values_to_match_regex` / `_not_match_regex` | Khớp regex |
| `expect_column_values_to_match_regex_list` | Khớp 1 trong nhiều regex |

```yaml
- name: email_address
  data_tests:
    - dbt_expectations.expect_column_values_to_match_regex:
        regex: "^[^@]+@[^@]+\\.[^@]+$"
- name: country_region_code
  data_tests:
    - dbt_expectations.expect_column_value_lengths_to_equal:
        value: 2
```

Lưu ý regex: cú pháp phụ thuộc warehouse (Snowflake `regexp_like`, BigQuery RE2, Postgres `~`). Escape `\` trong YAML cần gấp đôi. Có tham số `is_raw` và `flags` cho trường hợp đặc biệt.

### 5. Aggregate — thống kê cả cột

| Test | Kiểm tra |
|---|---|
| `expect_column_min_to_be_between` / `max` / `mean` / `median` / `sum` / `stdev` | Thống kê cột trong khoảng |
| `expect_column_quantile_values_to_be_between` | Phân vị trong khoảng |
| `expect_column_distinct_count_to_equal` / `_be_greater_than` / `_be_less_than` | Số giá trị distinct |
| `expect_column_distinct_count_to_equal_other_table` | Distinct count khớp bảng khác |
| `expect_column_distinct_values_to_be_in_set` / `_contain_set` / `_equal_set` | Tập giá trị distinct |
| `expect_column_proportion_of_unique_values_to_be_between` | Tỉ lệ unique |
| `expect_column_unique_value_count_to_be_between` | Số giá trị xuất hiện đúng 1 lần |
| `expect_column_most_common_value_to_be_in_set` | Giá trị phổ biến nhất thuộc tập |

Khác nhóm 3: nhóm 3 kiểm **từng dòng**, nhóm 5 kiểm **thống kê cả cột**. Ví dụ: từng đơn có thể 0–100k USD (nhóm 3), nhưng **trung bình** đơn phải trong 500–5,000 (nhóm 5) — bắt lỗi nhân nhầm đơn vị mà từng dòng vẫn "hợp lệ".

```yaml
- name: total_due_amount
  data_tests:
    - dbt_expectations.expect_column_mean_to_be_between:
        min_value: 500
        max_value: 5000
        group_by: [order_year]
- name: territory_id
  data_tests:
    - dbt_expectations.expect_column_distinct_count_to_equal:
        value: 10
```

### 6. Multi-column

| Test | Kiểm tra |
|---|---|
| `expect_column_pair_values_A_to_be_greater_than_B` | Cột A > (hoặc ≥) cột B |
| `expect_column_pair_values_to_be_equal` | 2 cột bằng nhau |
| `expect_column_pair_values_to_be_in_set` | Cặp giá trị thuộc tập cặp hợp lệ |
| `expect_compound_columns_to_be_unique` | Tổ hợp cột duy nhất |
| `expect_multicolumn_sum_to_equal` | Tổng nhiều cột = giá trị |
| `expect_select_column_values_to_be_unique_within_record` | Các cột trong cùng dòng khác nhau |

```yaml
models:
  - name: fct_sales
    data_tests:
      - dbt_expectations.expect_column_pair_values_A_to_be_greater_than_B:
          column_A: due_date
          column_B: order_date
          or_equal: true
      - dbt_expectations.expect_compound_columns_to_be_unique:
          column_list: [order_id, order_line_id]
```

### 7. Distributional — phát hiện bất thường

| Test | Kiểm tra |
|---|---|
| `expect_column_values_to_be_within_n_stdevs` | Giá trị không lệch quá N độ lệch chuẩn so với trung bình |
| `expect_column_values_to_be_within_n_moving_stdevs` | Giá trị theo thời gian (vd doanh thu ngày) không lệch quá N độ lệch chuẩn của **cửa sổ trượt** |
| `expect_row_values_to_have_data_for_every_n_datepart` | Mỗi ngày/tuần đều có dữ liệu, không có lỗ hổng |

```yaml
models:
  - name: fct_daily_sales
    columns:
      - name: revenue
        data_tests:
          - dbt_expectations.expect_column_values_to_be_within_n_moving_stdevs:
              date_column_name: order_date
              period: day
              lookback_periods: 1
              trend_periods: 7
              test_periods: 14
              sigma_threshold: 3
              severity: warn
  - name: fct_sales
    data_tests:
      - dbt_expectations.expect_row_values_to_have_data_for_every_n_datepart:
          date_col: order_date
          date_part: day
          test_start_date: "2011-06-01"
          test_end_date: "2014-06-30"
```

Đây là bước đầu của **anomaly detection** — chủ đề làm sâu ở tuần 9 với Elementary. Tham số của `within_n_moving_stdevs` khá nhiều; đọc kỹ README và xem SQL compile để hiểu nó tính gì trước khi dùng.

---

## Khi nào dùng test của ai?

| Nhu cầu | dbt Core | dbt-utils | dbt-expectations |
|---|---|---|---|
| Không null | `not_null` | — | `..._not_be_null` (+ `row_condition`) |
| Duy nhất 1 cột | `unique` | — | `..._be_unique` |
| Khoá ghép | — | `unique_combination_of_columns` | `expect_compound_columns_to_be_unique` |
| Thuộc tập giá trị | `accepted_values` | `not_accepted_values` | `..._be_in_set` |
| Khoá ngoại | `relationships` | `relationships_where` | — |
| Khoảng giá trị | — | `accepted_range` | `..._be_between` |
| Biểu thức tuỳ ý | — | `expression_is_true` | — |
| Regex / độ dài chuỗi | — | — | ✅ |
| Thống kê cột (mean, median, distinct) | — | — | ✅ |
| Schema (tập cột, kiểu) | contract (3.4) | — | ✅ |
| Dữ liệu mới | source freshness | `recency` | `..._have_recent_data` |
| Đối soát 2 bảng | — | `equal_rowcount`, `equality` | `..._equal_other_table`, `aggregation_to_equal_other_table` |
| Bất thường theo thời gian | — | — | `within_n_moving_stdevs` |

Nguyên tắc:
1. Có ở **dbt Core** thì dùng dbt Core (đơn giản, ai cũng đọc được).
2. Trùng giữa dbt-utils và dbt-expectations → **chọn một, thống nhất** trong project.
3. dbt-expectations dùng cho cái **chỉ nó có**: regex, thống kê, schema, anomaly.

## Chiến lược test theo tầng

| Tầng | Test nên có |
|---|---|
| sources | freshness, row count > 0, khoá nguồn unique/not null |
| staging | unique/not_null khoá, accepted_values, regex định dạng (email, mã) |
| intermediate | ít test; chủ yếu khoá sau khi join (bắt fan-out) |
| marts | khoá ghép, quan hệ cột (A > B), khoảng giá trị, đối soát tổng với nguồn, thống kê/anomaly (`warn`) |

Đừng test mọi thứ ở mọi tầng: test trùng lặp làm chậm build và gây "mệt mỏi cảnh báo".

## Lỗi hay gặp

- Thiếu var `dbt_date:time_zone` → test thời gian lỗi compile.
- Còn dùng `calogica/dbt_expectations` cho project mới.
- Regex viết theo cú pháp Python, warehouse không hiểu.
- Test thống kê/anomaly để `severity: error` → fail vì biến động bình thường (cuối tuần, lễ).
- Dùng `expect_column_values_to_be_unique` thay `unique` của dbt Core mà không có lý do.

## Bài tập trên adventure_works

- [ ] Khai báo var `dbt_date:time_zone`
- [ ] Mỗi nhóm 1–6 có ít nhất 1 test trên model thật (6 test)
- [ ] `ship_date` not null với `row_condition`
- [ ] Đối soát `sum(line_total_amount)` của `fct_sales` với nguồn bằng `expect_table_aggregation_to_equal_other_table`
- [ ] `fct_daily_sales` + `expect_column_values_to_be_within_n_moving_stdevs` (`warn`)
- [ ] Mở `target/compiled/` của 1 test dbt-expectations, đọc SQL nó sinh ra
- [ ] README: bảng "loại test – package – lý do chọn"

## Câu hỏi tự kiểm tra

1. Vì sao nên dùng bản Metaplane thay vì Calogica?
2. `expect_column_values_to_be_between` khác `expect_column_mean_to_be_between` thế nào? Cho ví dụ lỗi chỉ cái sau bắt được.
3. Diễn tả "ship_date không null khi đơn đã giao" bằng test nào?
4. Trùng chức năng giữa dbt-utils và dbt-expectations thì chọn thế nào?
5. Vì sao test anomaly nên để `warn`?
