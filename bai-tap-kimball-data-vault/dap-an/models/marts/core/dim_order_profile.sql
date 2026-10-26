-- Junk dimension: gom các cờ/thuộc tính ít giá trị của đơn (kênh × thanh toán × quà tặng) vào 1 dimension nhỏ
-- thay vì 3 dimension tí hon hoặc để rời rạc trong fact. Chỉ lấy các tổ hợp THỰC SỰ xuất hiện.
with combos as (
    select distinct channel, payment_method, is_gift
    from {{ ref('int_sales__lines') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['channel', 'payment_method', 'is_gift']) }}   as order_profile_key,
    channel,
    case when channel = 'store' then 'Cửa hàng' else 'Online' end                    as channel_group,
    payment_method,
    is_gift
from combos
