-- TODO J1: thay phép chia cents bằng macro cents_to_dollars()
-- Lưu ý bài I7: từ ngày 4 nguồn có thêm cột channel. Model này đang liệt kê cột tường minh,
-- nên sẽ KHÔNG tự có channel — bạn phải tự thêm khi tới bài I7.
select
    order_id,
    customer_id,
    order_date,
    status                                  as order_status,
    round(amount_cents / 100.0, 2)          as amount,
    updated_at,
    _loaded_at
from {{ source('raw', 'orders') }}
