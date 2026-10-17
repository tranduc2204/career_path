-- S7 — tự dựng SCD2 bằng incremental (không dùng snapshot). Theo dõi city, tier.
{{ config(
    materialized='incremental',
    incremental_strategy='delete+insert',
    unique_key='scd_id'
) }}

with source as (
    select
        customer_id,
        city,
        tier,
        {{ dbt_utils.generate_surrogate_key(['city', 'tier']) }} as row_hash,
        _loaded_at
    from {{ ref('stg_customers') }}
),

{% if is_incremental() %}

current_rows as (
    select * from {{ this }} where is_current
),

changed as (                -- khách mới, hoặc city/tier khác phiên bản đang mở
    select s.*
    from source s
    left join current_rows c using (customer_id)
    where c.customer_id is null or c.row_hash <> s.row_hash
),

deleted as (                -- đang mở trong dim nhưng đã biến mất khỏi nguồn
    select c.customer_id
    from current_rows c
    left join source s using (customer_id)
    where s.customer_id is null
),

closed as (                 -- đóng phiên bản cũ (giữ nguyên scd_id để delete+insert ghi đè)
    select
        c.scd_id,
        c.customer_id,
        c.city,
        c.tier,
        c.row_hash,
        c.valid_from,
        coalesce(ch._loaded_at, (select max(_loaded_at) from source)) as valid_to,
        false as is_current
    from current_rows c
    left join changed ch using (customer_id)
    where ch.customer_id is not null
       or c.customer_id in (select customer_id from deleted)
),

{% else %}

changed as (
    select * from source
),

{% endif %}

new_versions as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id', '_loaded_at']) }} as scd_id,
        customer_id,
        city,
        tier,
        row_hash,
        _loaded_at                      as valid_from,
        cast(null as timestamp)         as valid_to,
        true                            as is_current
    from changed
)

select * from new_versions
{% if is_incremental() %}
union all
select * from closed
{% endif %}
