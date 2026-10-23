{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key='event_id'
    )
}}

with events as (
    select *
    from {{ ref('stg_events') }}
    {{get_incremental_filter(column_name='event_ts')}}
)
select event_id, user_id, event_type, event_ts
from events
qualify row_number() over (partition by event_id order by event_ts desc) = 1
