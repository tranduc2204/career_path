-- Quan hệ đơn ↔ khách. Link luôn là nhiều-nhiều và chỉ thêm, không bao giờ sửa.
{{ automate_dv.link(src_pk='LINK_ORDER_CUSTOMER_HK',
                    src_fk=['ORDER_HK', 'CUSTOMER_HK'],
                    src_ldts='LOAD_DATETIME',
                    src_source='RECORD_SOURCE',
                    source_model=['v_stg_shop__orders', 'v_stg_pos__sales']) }}
