{{ automate_dv.hub(src_pk='CATEGORY_HK',
                   src_nk='category_code',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model=['v_stg_erp__categories', 'v_stg_erp__products']) }}
