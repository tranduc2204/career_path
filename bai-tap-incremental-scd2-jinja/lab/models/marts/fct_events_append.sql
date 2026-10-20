
{{
    config(
        materialized='incremental',
        incremental_strategy='append',
    )
}}

with fct_events_append as (
    select 
        event_id,
        user_id, 
        event_type, 
        event_ts,
        _loaded_at
    from {{ ref('stg_events') }}
)
select *
from fct_events_append

{% if is_incremental() %}
where _loaded_at > (select max (_loaded_at) from {{ this }} )
{% endif %}



