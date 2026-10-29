{% snapshot snap_customers_check %}

{{
    config(
        target_schema='snapshot',
        unique_key='customer_id',
        strategy='check',
        check_cols=['city', 'tier'],
        hard_deletes= 'new_record',
    )
}}

select * 
from {{ source('raw', 'customers')}}


{% endsnapshot %}
