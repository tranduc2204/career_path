-- B7 / P3 / P6 — quy tắc "đơn nào tính doanh thu" đặt ở MỘT chỗ duy nhất.
-- Đổi quy tắc (thêm trạng thái mới, soft delete...) chỉ sửa ở đây và var non_revenue_statuses.
select
    *,
    order_status not in (
        {%- for s in var('non_revenue_statuses') %}'{{ s }}'{{ ", " if not loop.last }}{% endfor -%}
    )
    and not is_deleted                              as is_revenue_order
from {{ ref('stg_orders') }}
