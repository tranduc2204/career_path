-- Time spine: 1 dòng / ngày. MetricFlow dùng bảng này cho cumulative metric, offset_window,
-- fill_nulls_with + join_to_timespine. Phải phủ hết khoảng dữ liệu + khoảng bạn sẽ truy vấn.
select cast(range as date) as date_day
from range(date '2025-01-01', date '2028-01-01', interval 1 day)
