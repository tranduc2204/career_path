

--S7 

{{
    config(
        materialized='incremental',
        incremental_strategy='delete+insert',
        
    )
}}

with source as (
    select 
        
        *,
        {{ dbt_utils.generate_surrogate_key (['city',  'tier']) }} AS row_hash,
    from {{ ref('stg_customers') }}
), 
{% if is_incremental() %}

current_rows as (
    select *
    from {{ this }}
)
changed as (
    select *
    from source  
)



{% else %}

changed as (
    select 
        *
    from source
)

{% endif %}

new_version as (
    select 
        {{ dbt_utils.generate_surrogate_key (['city',  'tier']) }} AS row_hash,

    from changed
)

select *
from new_version






