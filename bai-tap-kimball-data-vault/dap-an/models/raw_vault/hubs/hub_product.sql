{{ automate_dv.hub(src_pk='PRODUCT_HK',
                   src_nk='sku',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model=['v_stg_erp__products', 'v_stg_shop__order_lines', 'v_stg_pos__sales']) }}
