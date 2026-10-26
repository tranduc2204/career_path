-- Danh mục KHÔNG nằm ở đây: quan hệ giữa 2 khái niệm kinh doanh luôn là link (link_product_category).
{{ automate_dv.sat(src_pk='PRODUCT_HK',
                   src_hashdiff='PRODUCT_HASHDIFF',
                   src_payload=['product_name', 'brand', 'list_price'],
                   src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model='v_stg_erp__products') }}
