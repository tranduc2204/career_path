-- Effectivity satellite: link nào ĐANG hiệu lực. Driving key = sản phẩm (1 sản phẩm chỉ thuộc 1 danh mục tại một thời điểm).
-- is_auto_end_dating: khi sản phẩm xuất hiện với danh mục mới, tự đóng (END_DATE) link với danh mục cũ.
{{ config(is_auto_end_dating=true) }}

{{ automate_dv.eff_sat(src_pk='LINK_PRODUCT_CATEGORY_HK',
                       src_dfk=['PRODUCT_HK'],
                       src_sfk=['CATEGORY_HK'],
                       src_start_date='START_DATE',
                       src_end_date='END_DATE',
                       src_eff='EFFECTIVE_FROM',
                       src_ldts='LOAD_DATETIME',
                       src_source='RECORD_SOURCE',
                       source_model='v_stg_erp__products') }}
