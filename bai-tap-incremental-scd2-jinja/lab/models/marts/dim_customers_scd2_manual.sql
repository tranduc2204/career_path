

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
        {{ dbt_utils.generate_surrogate_key(['city', 'tier'])}} as row_hash
    from {{ ref( 'stg_customers' ) }}
),

{% if is_incremental() %}

    current_rows  as(
        select *
        from {{ this }}
        where is_current
    ),
    changed as (
        select *
        from source so
        left join current_rows cr  on so.customer_id = cr.customer_id
        where so.row_hash <> cr.row_hash
    ), 
    deleted as (
        select distinct customer_id 
        from current_rows cr
        where customer_id not in (select distinct customer_id from source)
    ),

    closed as (
        select 
            cr.scd_id,
            cr.customer_id, 
            cr.city,
            cr.tier,
            cr.row_hash,
            cr.valid_from,
            coalesce(ch._loaded_at, (select max(_loaded_at) from source)) as valid_to,
            false as is_current
        from current_rows cr 
        left join changed ch on cr.customer_id = ch.customer_id
        where ch.customer_id is not null
            or cr.customer_id in (select distinct customer_id  from deleted)
    ),

{% else %}

    changed as (
        select *
        from source
    ),

{% endif %}

new_version as (
    select 
        {{ dbt_utils.generate_surrogate_key(['customer_id', '_loaded_at']) }} as scd_id,
        customer_id, 
        city,
        tier,
        row_hash,
        _loaded_at  as valid_from,
        cast(null as timestamp) as valid_to,
        true as is_current
    from changed
)
select *
from new_version
{% if is_incremental() %}
union all
select * from closed
{% endif %}