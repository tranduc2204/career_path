-- dim_customer dựng từ VAULT. Phải ra ĐÚNG Y HỆT dim_customer của tuần 4 (cùng khoá, cùng phiên bản).
-- Phiên bản theo THỜI GIAN NGHIỆP VỤ (EFFECTIVE_FROM = ngày file CRM), không theo LOAD_DATETIME (giờ nạp).
-- Inferred member đến tự nhiên: hub_customer có khách mà satellite CRM chưa có dòng nào.
with status as (
    select
        h.customer_code,
        s.city,
        s.loyalty_tier,
        s.EFFECTIVE_FROM,
        row_number() over (partition by s.CUSTOMER_HK order by s.EFFECTIVE_FROM)   as version_seq
    from {{ ref('sat_customer_crm_status') }} as s
    inner join {{ ref('hub_customer') }} as h using (CUSTOMER_HK)
),

versions as (
    select
        customer_code,
        city,
        loyalty_tier,
        case when version_seq = 1 then timestamp '1900-01-01' else EFFECTIVE_FROM end  as valid_from
    from status
),

ranged as (
    select
        *,
        coalesce(lead(valid_from) over (partition by customer_code order by valid_from),
                 timestamp '9999-12-31')                                           as valid_to
    from versions
),

profile as (
    select h.customer_code, p.full_name, p.email
    from {{ ref('sat_customer_crm_profile') }} as p
    inner join {{ ref('hub_customer') }} as h using (CUSTOMER_HK)
    qualify row_number() over (partition by p.CUSTOMER_HK order by p.LOAD_DATETIME desc) = 1
),

known as (
    select r.customer_code, pr.full_name, pr.email, r.city, r.loyalty_tier, r.valid_from, r.valid_to,
           false as is_inferred
    from ranged as r
    inner join profile as pr using (customer_code)
),

inferred as (
    select
        h.customer_code,
        'Chưa xác định'             as full_name,
        cast(null as varchar)       as email,
        'Chưa xác định'             as city,
        'Chưa xác định'             as loyalty_tier,
        timestamp '1900-01-01'      as valid_from,
        timestamp '9999-12-31'      as valid_to,
        true                        as is_inferred
    from {{ ref('hub_customer') }} as h
    where h.customer_code <> '-2'      -- zero key của khách vãng lai không phải khách thật
      and not exists (
          select 1 from {{ ref('sat_customer_crm_status') }} as s where s.CUSTOMER_HK = h.CUSTOMER_HK
      )
),

all_versions as (
    select * from known
    union all
    select * from inferred
)

select
    {{ dbt_utils.generate_surrogate_key(['customer_code', 'valid_from']) }}    as customer_key,
    customer_code,
    full_name,
    email,
    city,
    loyalty_tier,
    valid_from,
    valid_to,
    valid_to = timestamp '9999-12-31'                                       as is_current,
    is_inferred
from all_versions

union all

select
    '-1', '-1', 'Khách vãng lai / không xác định', null, 'Không xác định', 'Không xác định',
    timestamp '1900-01-01', timestamp '9999-12-31', true, false
