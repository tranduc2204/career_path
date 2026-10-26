{{ automate_dv.sat(src_pk='CATEGORY_HK',
                   src_hashdiff='CATEGORY_HASHDIFF',
                   src_payload=['category_name', 'parent_code'],
                   src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model='v_stg_erp__categories') }}
