-- I6 — không tin _loaded_at: lọc theo event_ts + lookback, dedupe bằng unique_key
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='event_id'
) }}

select event_id, user_id, event_type, event_ts
from {{ ref('stg_events') }}
{{ get_incremental_filter('event_ts') }}
qualify row_number() over (partition by event_id order by _loaded_at) = 1
