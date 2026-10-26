-- Đơn online (W....) và hoá đơn cửa hàng (HN-..., HCM-...) cùng là khái niệm "đơn bán hàng" → chung 1 hub.
{{ automate_dv.hub(src_pk='ORDER_HK',
                   src_nk='order_number',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model=['v_stg_shop__orders', 'v_stg_pos__sales']) }}
