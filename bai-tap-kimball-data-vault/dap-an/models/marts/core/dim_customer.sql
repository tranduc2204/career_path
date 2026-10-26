-- SCD Type 2 dựng lại hoàn toàn từ lịch sử file CRM (không cần snapshot vì nguồn đã giữ lịch sử).
--   * Theo dõi lịch sử (Type 2): city, loyalty_tier.
--   * Ghi đè (Type 1): full_name, email → mọi phiên bản mang giá trị MỚI NHẤT.
--   * Phiên bản đầu tiên hiệu lực từ 1900-01-01 → khoá của "inferred member" và phiên bản thật đầu tiên trùng nhau.
--   * Inferred member: khách xuất hiện trong đơn nhưng CRM chưa có.  Unknown member '-1': khách vãng lai.
with crm as (
    select * from {{ ref('stg_crm__customers') }}
),

compared as (
    select
        customer_code,
        extract_date,
        city,
        loyalty_tier,
        row_number() over w                 as file_seq,
        lag(city) over w                    as prev_city,
        lag(loyalty_tier) over w            as prev_tier
    from crm
    window w as (partition by customer_code order by extract_date)
),

changes as (
    select
        customer_code,
        city,
        loyalty_tier,
        case when file_seq = 1 then timestamp '1900-01-01'
             else cast(extract_date as timestamp) end      as valid_from
    from compared
    where file_seq = 1
       or city is distinct from prev_city
       or loyalty_tier is distinct from prev_tier
),

versions as (
    select
        *,
        coalesce(lead(valid_from) over (partition by customer_code order by valid_from),
                 timestamp '9999-12-31')                  as valid_to
    from changes
),

latest as (
    select customer_code, full_name, email
    from crm
    qualify row_number() over (partition by customer_code order by extract_date desc) = 1
),

crm_versions as (
    select
        v.customer_code, l.full_name, l.email, v.city, v.loyalty_tier, v.valid_from, v.valid_to,
        false as is_inferred
    from versions as v
    inner join latest as l using (customer_code)
),

seen_in_sales as (
    select customer_code from {{ ref('stg_shop__orders') }}
    union
    select customer_code from {{ ref('stg_pos__sales') }} where customer_code is not null
),

inferred as (
    select
        customer_code,
        'Chưa xác định'                 as full_name,
        cast(null as varchar)           as email,
        'Chưa xác định'                 as city,
        'Chưa xác định'                 as loyalty_tier,
        timestamp '1900-01-01'          as valid_from,
        timestamp '9999-12-31'          as valid_to,
        true                            as is_inferred
    from seen_in_sales
    where customer_code not in (select customer_code from latest)
),

all_versions as (
    select * from crm_versions
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
