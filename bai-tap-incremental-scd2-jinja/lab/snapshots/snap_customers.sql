
{% snapshot snap_customers %}

{{
    config(
        target_schema='snapshot',
        unique_key='customer_id',
        strategy='timestamp',
        updated_at='updated_at',
        
    )
}}

select *
from {{ source('raw', 'customers')}}


{% endsnapshot %}











