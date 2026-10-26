-- Point-In-Time: với mỗi khách × mỗi mốc as-of, lưu SẴN con trỏ (hash key + LOAD_DATETIME) tới dòng satellite
-- đang hiệu lực. Truy vấn sau đó chỉ cần equi-join thay vì join theo khoảng thời gian trên nhiều satellite.
{{ config(materialized='pit_incremental') }}

{{ automate_dv.pit(src_pk='CUSTOMER_HK',
                   as_of_dates_table='as_of_date',
                   satellites={
                       'sat_customer_crm_profile': {'pk': {'PK': 'CUSTOMER_HK'}, 'ldts': {'LDTS': 'LOAD_DATETIME'}},
                       'sat_customer_crm_status': {'pk': {'PK': 'CUSTOMER_HK'}, 'ldts': {'LDTS': 'LOAD_DATETIME'}}
                   },
                   stage_tables_ldts={'v_stg_crm__customers': 'LOAD_DATETIME'},
                   src_ldts='LOAD_DATETIME',
                   source_model='hub_customer') }}
