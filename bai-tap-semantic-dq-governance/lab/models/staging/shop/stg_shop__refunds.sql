select
    refund_id,
    order_id,
    refund_ts,
    cast(refund_ts as date)   as refund_date,
    cast(amount as bigint)    as refund_amount,
    reason,
    _loaded_at
from {{ source('shop', 'refunds') }}
