-- Quan hệ sản phẩm ↔ danh mục. Khi SKU07 đổi danh mục, link MỚI được thêm; link cũ vẫn còn đó.
-- Muốn biết link nào đang hiệu lực → effectivity satellite (sats/eff_sat_product_category).
{{ automate_dv.link(src_pk='LINK_PRODUCT_CATEGORY_HK',
                    src_fk=['PRODUCT_HK', 'CATEGORY_HK'],
                    src_ldts='LOAD_DATETIME',
                    src_source='RECORD_SOURCE',
                    source_model='v_stg_erp__products') }}
