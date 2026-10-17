{# I8 — khai báo event_time để microbatch lọc được input theo từng batch #}
{{ config(event_time='event_ts') }}

select
    event_id,
    user_id,
    event_type,
    event_ts,
    _loaded_at
from {{ source('raw', 'events') }}
