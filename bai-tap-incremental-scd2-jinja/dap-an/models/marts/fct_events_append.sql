-- I1 — append thuần
{{ config(materialized='incremental', incremental_strategy='append') }}

select event_id, user_id, event_type, event_ts, _loaded_at
from {{ ref('stg_events') }}
{% if is_incremental() %}
where _loaded_at > (select max(_loaded_at) from {{ this }})
{% endif %}
