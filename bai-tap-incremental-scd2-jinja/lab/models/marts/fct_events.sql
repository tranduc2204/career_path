{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        unique_key='event_id'
    )
}}
with events as (
    select 
        *
    from {{ ref('stg_events') }}
)
select *
from events
{% if is_incremental() %}
where _loaded_at > (select max (_loaded_at) from {{ this }} )
{% endif %}
qualify row_number() over (partition by event_id order by _loaded_at) = 1

