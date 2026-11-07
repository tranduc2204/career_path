-- 1 dòng / sự kiện CDC. Loại bản phát lại của connector (cùng lsn) ngay tại staging.
select distinct
    lsn, op, commit_ts, txn_id, account_id, booking_ts, value_date,
    amount, upper(currency) as currency, upper(txn_type) as txn_type, upper(channel) as channel, upper(status) as status
from {{ source('core', 'txn_cdc') }}
