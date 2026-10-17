-- I2 — chống trùng: unique_key + dedupe trong batch. I9: chặn full refresh nhầm.
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='event_id',
    on_schema_change='fail',
    full_refresh=false
) }}

with batch as (
    select * from {{ ref('stg_events') }}
    {% if is_incremental() %}
    where _loaded_at > (select max(_loaded_at) from {{ this }})
    {% endif %}
)

select event_id, user_id, event_type, event_ts, _loaded_at
from batch
qualify row_number() over (partition by event_id order by _loaded_at) = 1
