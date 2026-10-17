{# I8 — khai báo event_time để microbatch lọc được input theo từng batch #}
{{ config(event_time='event_ts') }}

-- Không dedupe ở đây (bài I1/I2 cần thấy dữ liệu trùng).
-- P5: sự kiện không có event_id thì không định danh được → loại ở staging.
select
    event_id,
    user_id,
    event_type,
    event_ts,
    _loaded_at
from {{ source('raw', 'events') }}
where event_id is not null
