-- Mỗi lần trạng thái đơn đổi (placed → paid → cancelled/returned) là 1 dòng mới. Nguồn ghi đè, nên nếu
-- dbt không chạy ngày nào thì thay đổi của ngày đó MẤT VĨNH VIỄN (giống snapshot ở GĐ1).
{{ automate_dv.sat(src_pk='ORDER_HK',
                   src_hashdiff='ORDER_SHOP_HASHDIFF',
                   src_payload=['channel', 'payment_method', 'is_gift', 'shipping_fee', 'total_amount',
                                'order_status', 'order_ts', 'paid_at', 'cancelled_at'],
                   src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model='v_stg_shop__orders') }}
