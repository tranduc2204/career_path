{{ config(apply_source_filter=true) }}

{{ automate_dv.sat(src_pk='ORDER_HK',
                   src_hashdiff='ORDER_POS_HASHDIFF',
                   src_payload=['store_code', 'payment_method', 'sale_ts'],
                   src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model='v_stg_pos__sales') }}
