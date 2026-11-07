-- Trạng thái HIỆN TẠI của mỗi giao dịch = sự kiện có lsn lớn nhất; bỏ giao dịch đã xoá.
select *
from {{ ref('stg_core__txn_cdc') }}
qualify row_number() over (partition by txn_id order by lsn desc) = 1
    and op <> 'd'
