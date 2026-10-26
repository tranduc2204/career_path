-- Multi-active satellite: 1 khách có NHIỀU số cùng lúc. Khoá con (child dependent key) = phone_type.
-- Khi bất kỳ số nào trong tập đổi, CẢ TẬP mới được ghi lại với LOAD_DATETIME mới.
{{ automate_dv.ma_sat(src_pk='CUSTOMER_HK',
                      src_cdk=['phone_type'],
                      src_hashdiff='PHONE_HASHDIFF',
                      src_payload=['phone_number'],
                      src_eff='EFFECTIVE_FROM',
                      src_ldts='LOAD_DATETIME',
                      src_source='RECORD_SOURCE',
                      source_model='v_stg_crm__customer_phones') }}
