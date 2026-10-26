-- Tách satellite theo TỐC ĐỘ THAY ĐỔI và ĐỘ NHẠY: profile (tên, email = dữ liệu cá nhân, hiếm đổi) riêng với status.
-- apply_source_filter: stage chứa MỌI file CRM, chỉ xét bản ghi mới hơn bản đã có trong satellite.
-- Thiếu dòng này → từ ngày 2 satellite bị chèn lại lịch sử cũ (test unique (CUSTOMER_HK, LOAD_DATETIME) đỏ).
{{ config(apply_source_filter=true) }}

{{ automate_dv.sat(src_pk='CUSTOMER_HK',
                   src_hashdiff='CUSTOMER_PROFILE_HASHDIFF',
                   src_payload=['full_name', 'email'],
                   src_eff='EFFECTIVE_FROM',
                   src_ldts='LOAD_DATETIME',
                   src_source='RECORD_SOURCE',
                   source_model='v_stg_crm__customers') }}
