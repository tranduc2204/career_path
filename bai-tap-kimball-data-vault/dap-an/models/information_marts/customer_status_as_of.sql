-- Dùng PIT: trạng thái khách mà kho BIẾT tại mỗi lần nạp. Chỉ toàn equi-join.
select
    h.customer_code,
    p.AS_OF_DATE                as as_of_date,
    pr.full_name,
    pr.email,
    st.city,
    st.loyalty_tier
from {{ ref('pit_customer') }} as p
inner join {{ ref('hub_customer') }} as h
    on h.CUSTOMER_HK = p.CUSTOMER_HK
left join {{ ref('sat_customer_crm_status') }} as st
    on  st.CUSTOMER_HK = p.sat_customer_crm_status_PK
    and st.LOAD_DATETIME = p.sat_customer_crm_status_LDTS
left join {{ ref('sat_customer_crm_profile') }} as pr
    on  pr.CUSTOMER_HK = p.sat_customer_crm_profile_PK
    and pr.LOAD_DATETIME = p.sat_customer_crm_profile_LDTS
where h.customer_code <> '-2'
