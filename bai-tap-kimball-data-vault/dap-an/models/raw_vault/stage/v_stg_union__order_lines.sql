-- automate_dv.nh_link chỉ nhận MỘT source_model → gộp dòng đơn của 2 hệ thống thành 1 stage.
-- Hash key đã tính ở từng stage gốc theo cùng công thức nên gộp được an toàn.
select ORDER_LINE_HK, ORDER_HK, PRODUCT_HK, line_no, quantity, unit_price, LOAD_DATETIME, RECORD_SOURCE
from {{ ref('v_stg_shop__order_lines') }}

union all

select ORDER_LINE_HK, ORDER_HK, PRODUCT_HK, line_no, quantity, unit_price, LOAD_DATETIME, RECORD_SOURCE
from {{ ref('v_stg_pos__sales') }}
