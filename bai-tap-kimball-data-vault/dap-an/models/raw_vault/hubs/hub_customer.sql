-- 1 dòng / khách hàng DUY NHẤT trên toàn công ty, gom từ 3 hệ thống. Hub chỉ có business key, không có thuộc tính.
-- RECORD_SOURCE + LOAD_DATETIME cho biết khách được thấy LẦN ĐẦU ở đâu, lúc nào (C013: SHOP trước CRM).
{{ automate_dv.hub(src_pk='CUSTOMER_HK',
                   src_nk='customer_code',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model=['v_stg_crm__customers', 'v_stg_shop__orders', 'v_stg_pos__sales']) }}
