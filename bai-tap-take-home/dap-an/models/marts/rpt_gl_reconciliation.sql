-- Đối soát: tổng số dư tài khoản (tính từ giao dịch) vs số dư sổ cái, theo ngày × sản phẩm × loại tiền.
with acct as (
    select b.balance_date, a.product, a.currency, sum(b.balance) as total_account_balance
    from {{ ref('fct_account_daily_balance') }} b
    join {{ ref('stg_core__accounts') }} a using (account_id)
    group by 1, 2, 3
)
select
    g.balance_date,
    g.product,
    g.currency,
    coalesce(a.total_account_balance, 0)                       as total_account_balance,
    g.gl_balance,
    coalesce(a.total_account_balance, 0) - g.gl_balance        as difference,
    abs(coalesce(a.total_account_balance, 0) - g.gl_balance) < 0.01 as is_matched
from {{ source('gl', 'daily_balances') }} g
left join acct a using (balance_date, product, currency)
