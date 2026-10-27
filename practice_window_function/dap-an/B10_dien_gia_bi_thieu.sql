select
    san_pham_id,
    ngay,
    coalesce(
        -- forward fill: giá khác NULL gần nhất tính tới hôm nay
        last_value(gia ignore nulls) over (
            partition by san_pham_id order by ngay
            rows between unbounded preceding and current row
        ),
        -- back fill cho các ngày đầu chưa có giá: giá khác NULL đầu tiên phía sau
        first_value(gia ignore nulls) over (
            partition by san_pham_id order by ngay
            rows between current row and unbounded following
        )
    ) as gia_da_dien
from gia_niem_yet
