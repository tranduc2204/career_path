-- Non-historized link: giao dịch bất biến (dòng đơn không bao giờ sửa) → payload nằm luôn trong link, không cần satellite.
{{ automate_dv.nh_link(src_pk='ORDER_LINE_HK',
                       src_fk=['ORDER_HK', 'PRODUCT_HK'],
                       src_payload=['line_no', 'quantity', 'unit_price'],
                       src_ldts='LOAD_DATETIME',
                       src_source='RECORD_SOURCE',
                       source_model='v_stg_union__order_lines') }}
