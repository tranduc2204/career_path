{#
  Ngày nghiệp vụ mới nhất mà kho đã có dữ liệu = ngày của file CRM mới nhất
  (CRM xuất file full mỗi ngày, nên đây là "nhịp tim" đáng tin nhất của lab).
  Dùng khi cần dựng dãy ngày tới "hôm nay": dim_date, snapshot tồn kho, as_of_date...
      where d <= {{ business_date() }}
#}
{% macro business_date() %}
    (select max(extract_date) from {{ ref('stg_crm__customers') }})
{% endmacro %}
