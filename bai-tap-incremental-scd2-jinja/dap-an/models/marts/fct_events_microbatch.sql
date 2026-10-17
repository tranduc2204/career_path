-- I8 — microbatch: dbt tự chia theo ngày dựa trên event_time
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='event_ts',
    batch_size='day',
    begin='2025-12-29',
    lookback=2
) }}

select event_id, user_id, event_type, event_ts
from {{ ref('stg_events') }}
qualify row_number() over (partition by event_id order by _loaded_at) = 1
