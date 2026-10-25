{% snapshot snap_customers_check %}

{{
    config(
        target_schema='snapshot',
        unique_key='customer_id',
        strategy='check',
        check_cols=['city', 'tier'],
    )
}}

select *
from {{ source('raw', 'customers')}}


{% endsnapshot %}
