
{{
    config(
        materialized='incremental',
        incremental_strategy='append',
        
    )
}}

with events as (
    select *
    from {{ ref('stg_events') }}
) 
select 
    event_id, 
    user_id, 
    event_type, 
    event_ts,
    _loaded_at
from events
{% if is_incremental() %}  
    where _loaded_at > (select max(_loaded_at) from {{this}})
{% endif %}

