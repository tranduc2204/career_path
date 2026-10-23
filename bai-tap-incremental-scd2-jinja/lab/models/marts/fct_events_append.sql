
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
select *
from events
{% if is_incremental() %}  
    where _loaded_at > (select max(_loaded_at) from {{this}})
{% endif %}

