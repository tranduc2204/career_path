-- Grain: 1 dòng / giao dịch đã ghi sổ (POSTED), trạng thái hiện tại. Ngày nghiệp vụ = value_date.
select
    t.txn_id,
    t.account_id,
    a.customer_id,
    t.value_date,
    t.amount,
    t.currency,
    t.amount * fx.vnd_per_unit  as amount_vnd,
    t.txn_type,
    t.channel
from {{ ref('int_transactions__current') }} t
join {{ ref('stg_core__accounts') }} a using (account_id)
join {{ ref('int_fx_daily') }} fx on fx.currency = t.currency and fx.rate_date = t.value_date
where t.status = 'POSTED'
