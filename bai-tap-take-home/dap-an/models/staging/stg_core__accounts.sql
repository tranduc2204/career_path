select account_id, customer_id, upper(product) as product, upper(currency) as currency, open_date, close_date
from {{ source('core', 'accounts') }}
