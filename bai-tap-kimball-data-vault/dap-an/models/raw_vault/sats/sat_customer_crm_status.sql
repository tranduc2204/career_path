{{ config(apply_source_filter=true) }}

{{ automate_dv.sat(src_pk='CUSTOMER_HK',
                   src_hashdiff='CUSTOMER_STATUS_HASHDIFF',
                   src_payload=['city', 'loyalty_tier'],
                   src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model='v_stg_crm__customers') }}
