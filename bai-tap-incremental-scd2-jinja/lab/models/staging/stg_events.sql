-- Không dedupe ở đây: bài I1/I2 cần thấy dữ liệu trùng.
select
    event_id,
    user_id,
    event_type,
    event_ts,
    _loaded_at
from {{ source('raw', 'events') }}
