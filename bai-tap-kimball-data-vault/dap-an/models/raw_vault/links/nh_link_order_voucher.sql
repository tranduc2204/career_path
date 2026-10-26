{{ automate_dv.nh_link(src_pk='ORDER_VOUCHER_HK',
                       src_fk=['ORDER_HK', 'VOUCHER_HK'],
                       src_payload=['discount_amount'],
                       src_ldts='LOAD_DATETIME',
                       src_source='RECORD_SOURCE',
                       source_model='v_stg_shop__order_vouchers') }}
