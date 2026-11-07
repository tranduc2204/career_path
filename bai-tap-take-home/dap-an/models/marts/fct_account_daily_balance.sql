-- Grain: 1 dòng / tài khoản / ngày (DÀY ĐẶC) từ max(open_date, đầu kỳ) tới min(close_date, as_of_date).
-- Số dư luỹ kế từ ngày mở → phải tính trên toàn bộ lịch sử rồi mới cắt về đầu kỳ.
{% set start_date = '2026-11-01' %}
with spine as (
    select a.account_id, a.currency, cast(d as date) as balance_date
    from {{ ref('stg_core__accounts') }} a,
         range(a.open_date, coalesce(a.close_date, cast('{{ var("as_of_date") }}' as date)) + 1, interval 1 day) t(d)
),
daily as (
    select account_id, value_date, sum(amount) as net_amount
    from {{ ref('fct_transactions') }}
    group by 1, 2
),
running as (
    select
        s.account_id, s.currency, s.balance_date,
        sum(coalesce(d.net_amount, 0)) over (partition by s.account_id order by s.balance_date
                                             rows between unbounded preceding and current row) as balance
    from spine s
    left join daily d on d.account_id = s.account_id and d.value_date = s.balance_date
)
select
    r.account_id,
    r.balance_date,
    r.balance,
    r.balance * fx.vnd_per_unit as balance_vnd
from running r
join {{ ref('int_fx_daily') }} fx on fx.currency = r.currency and fx.rate_date = r.balance_date
where r.balance_date >= date '{{ start_date }}'
