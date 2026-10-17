-- S5 — dimension SCD2 từ snapshot + unknown member
with snap as (
    select * from {{ ref('snap_customers') }}
),

versions as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id', 'dbt_valid_from']) }} as customer_sk,
        customer_id,
        full_name,
        email,
        city,
        tier,
        dbt_valid_from                                              as valid_from,
        coalesce(dbt_valid_to, cast('9999-12-31' as timestamp))     as valid_to,
        dbt_valid_to is null                                        as is_current
    from snap
),

unknown_member as (
    select
        '-1'                                as customer_sk,
        -1                                  as customer_id,
        'Unknown'                           as full_name,
        cast(null as varchar)               as email,
        'Unknown'                           as city,
        'Unknown'                           as tier,
        cast('1900-01-01' as timestamp)     as valid_from,
        cast('9999-12-31' as timestamp)     as valid_to,
        true                                as is_current
)

select * from versions
union all
select * from unknown_member
