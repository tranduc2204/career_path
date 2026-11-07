select customer_id, full_name, lower(segment) as segment, upper(branch) as branch, created_at
from {{ source('core', 'customers') }}
