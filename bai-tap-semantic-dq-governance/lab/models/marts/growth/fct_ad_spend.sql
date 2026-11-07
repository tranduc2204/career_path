select ad_spend_id, spend_date, utm_source, spend
from {{ ref('stg_mkt__ad_spend') }}
