
{% {% macro get_incremental_filter(column_name, lookback_days=none) %}
    {%-if is_incremental() -%}
        {%- set days = lookback_days if lookback_days is not none else var('lookback_days', 0) -%}
        where {{ column_name }} >= (
            select {{ dbt.dateadd('day', -1 * days, 'max(' ~ column_name ~ ')') }}
            from {{ this }}
        )
{% endmacro %}%}

