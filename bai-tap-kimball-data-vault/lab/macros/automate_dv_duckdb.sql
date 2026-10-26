{#
  ===========================================================================
  Shim cho automate_dv 0.11.x trên DuckDB (package chưa hỗ trợ DuckDB chính thức).
  Đã kiểm chứng cho: stage, hub, link, nh_link, sat, eff_sat, ma_sat, xts, pit, bridge.

  Cơ chế: automate_dv gọi adapter.dispatch('<macro>', 'automate_dv'). Với target DuckDB, dbt tìm
  `duckdb__<macro>` theo search_order trong dbt_project.yml (project `lab` trước) rồi mới tới
  `default__<macro>` của package. Vì vậy:
    - Macro dựng bảng: dùng lại bản Postgres (cú pháp DuckDB rất gần Postgres, có DISTINCT ON).
    - pit, bridge, eff_sat: dùng bản default (cú pháp Snowflake; DuckDB hỗ trợ QUALIFY) nên KHÔNG khai báo ở đây.
    - Hash: trả về chuỗi hex IN HOA 32 ký tự (giống BigQuery khi không bật native hash) để bạn đọc được.
    - Ép kiểu ngày giờ: viết riêng bằng CAST chuẩn (bản Postgres dùng TO_DATE/TO_CHAR có format).
    - KHÔNG khai báo `duckdb__hash`: macro có sẵn dbt.hash() (dùng trong dbt_utils.generate_surrogate_key) cũng
      dispatch tên 'hash', và macro của project gốc sẽ ĐÈ lên nó → generate_surrogate_key hỏng.
      automate_dv tự rơi về default__hash (giống hệt bản Postgres) nên không cần shim.

  Đừng sửa file này khi làm bài. Trên Snowflake/BigQuery (adventure_works) không cần file này.
  ===========================================================================
#}

{%- macro duckdb__hub() -%}{{ return(automate_dv.postgres__hub(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__link() -%}{{ return(automate_dv.postgres__link(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__nh_link() -%}{{ return(automate_dv.postgres__nh_link(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__sat() -%}{{ return(automate_dv.postgres__sat(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__ma_sat() -%}{{ return(automate_dv.postgres__ma_sat(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__xts() -%}{{ return(automate_dv.postgres__xts(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__ref_table() -%}{{ return(automate_dv.postgres__ref_table(**kwargs)) }}{%- endmacro -%}

{%- macro duckdb__concat_ws() -%}{{ return(automate_dv.postgres__concat_ws(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__null_expression() -%}{{ return(automate_dv.postgres__null_expression(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__null_column_sql() -%}{{ return(automate_dv.postgres__null_column_sql(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__null_ghost() -%}{{ return(automate_dv.postgres__null_ghost(**kwargs)) }}{%- endmacro -%}
{%- macro duckdb__get_escape_characters() -%}{{ return(automate_dv.postgres__get_escape_characters(**kwargs)) }}{%- endmacro -%}

{%- macro duckdb__hash_alg_md5() -%}{%- do return("UPPER(MD5([HASH_STRING_PLACEHOLDER]))") -%}{%- endmacro -%}
{%- macro duckdb__hash_alg_sha256() -%}{%- do return("UPPER(SHA256([HASH_STRING_PLACEHOLDER]))") -%}{%- endmacro -%}
{%- macro duckdb__type_binary(for_dbt_compare=false) -%}VARCHAR{%- endmacro -%}

{%- macro duckdb__cast_date(column_str, as_string=false, alias=none) -%}
    {%- if as_string -%}CAST('{{ column_str }}' AS DATE){%- else -%}CAST({{ column_str }} AS DATE){%- endif -%}
    {%- if alias %} AS {{ alias }} {%- endif %}
{%- endmacro -%}

{%- macro duckdb__cast_datetime(column_str, as_string=false, alias=none, date_type=none) -%}
    CAST({{ column_str }} AS TIMESTAMP)
    {%- if alias %} AS {{ alias }} {%- endif %}
{%- endmacro -%}
