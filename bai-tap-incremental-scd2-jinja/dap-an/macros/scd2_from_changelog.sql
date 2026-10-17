{# J10 / S8 — dựng SCD2 từ CDC log. Chỉ tạo phiên bản mới khi tracked_columns đổi (gaps & islands). #}
{% macro scd2_from_changelog(relation, key, changed_at, tracked_columns, op_column='op', delete_value='D') %}
    {%- set row_hash = dbt_utils.generate_surrogate_key(tracked_columns) -%}
with ordered as (
    select
        *,
        {{ row_hash }} as _row_hash,
        lag({{ row_hash }}) over (partition by {{ key }} order by {{ changed_at }}) as _prev_hash,
        lag({{ op_column }}) over (partition by {{ key }} order by {{ changed_at }}) as _prev_op
    from {{ relation }}
),

changes as (
    -- giữ: bản ghi đầu tiên, bản ghi sau delete, bản ghi đổi giá trị theo dõi, và chính các delete
    select *
    from ordered
    where {{ op_column }} = '{{ delete_value }}'
       or _prev_hash is null
       or _prev_op = '{{ delete_value }}'
       or _row_hash <> _prev_hash
),

ranged as (
    select
        *,
        lead({{ changed_at }}) over (partition by {{ key }} order by {{ changed_at }}) as _next_changed_at
    from changes
)

select
    {{ dbt_utils.generate_surrogate_key([key, changed_at]) }} as scd_id,
    {{ key }},
    {%- for col in tracked_columns %}
    {{ col }},
    {%- endfor %}
    {{ changed_at }} as valid_from,
    _next_changed_at as valid_to,
    _next_changed_at is null as is_current
from ranged
where {{ op_column }} <> '{{ delete_value }}'
{% endmacro %}
