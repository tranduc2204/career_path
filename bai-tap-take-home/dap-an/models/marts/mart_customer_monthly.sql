-- Grain: 1 dòng / khách / tháng mà khách có ≥ 1 tài khoản mở (trong kỳ báo cáo).
with cust_day as (
    select a.customer_id, b.balance_date, sum(b.balance_vnd) as balance_vnd
    from {{ ref('fct_account_daily_balance') }} b
    join {{ ref('stg_core__accounts') }} a using (account_id)
    group by 1, 2
),
bal as (
    select customer_id, cast(date_trunc('month', balance_date) as date) as month_start,
           avg(balance_vnd) as avg_daily_balance_vnd
    from cust_day group by 1, 2
),
tx as (
    select customer_id, cast(date_trunc('month', value_date) as date) as month_start,
           sum(case when amount > 0 then amount_vnd else 0 end)  as total_inflow_vnd,
           sum(case when amount < 0 then -amount_vnd else 0 end) as total_outflow_vnd,
           count(*)                                               as txn_count,
           bool_or(channel <> 'SYSTEM')                           as is_active
    from {{ ref('fct_transactions') }}
    where value_date >= date '2026-11-01'
    group by 1, 2
)
select
    b.customer_id,
    b.month_start,
    coalesce(t.total_inflow_vnd, 0)   as total_inflow_vnd,
    coalesce(t.total_outflow_vnd, 0)  as total_outflow_vnd,
    coalesce(t.txn_count, 0)          as txn_count,
    b.avg_daily_balance_vnd,
    coalesce(t.is_active, false)      as is_active
from bal b
left join tx t using (customer_id, month_start)
