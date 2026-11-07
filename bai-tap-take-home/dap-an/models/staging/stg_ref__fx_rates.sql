select rate_date, upper(currency) as currency, vnd_per_unit
from {{ source('ref', 'fx_rates') }}
