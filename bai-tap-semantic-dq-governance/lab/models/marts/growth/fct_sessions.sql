select session_id, customer_id, session_start, session_date, device, utm_source, landing_page
from {{ ref('stg_web__sessions') }}
