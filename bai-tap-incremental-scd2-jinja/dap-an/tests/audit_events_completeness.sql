-- P5 — phát hiện sự kiện bị bỏ sót (vd đến trễ hơn lookback): mọi event_id hợp lệ ở staging phải có trong fact.
select event_id from {{ ref('stg_events') }}
except
select event_id from {{ ref('fct_events_by_ts') }}
