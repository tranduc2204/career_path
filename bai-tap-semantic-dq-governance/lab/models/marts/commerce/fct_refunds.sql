-- Grain: 1 dòng / lần hoàn tiền. Thời gian tổng hợp = ngày hoàn tiền (KHÔNG phải ngày đặt đơn).
select refund_id, order_id, refund_ts, refund_date, refund_amount, reason
from {{ ref('stg_shop__refunds') }}
