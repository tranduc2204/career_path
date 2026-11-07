# 18.4 Vòng kỹ thuật: live SQL, dbt, đọc code

## Các dạng vòng kỹ thuật cho AE

| Dạng | Thời lượng | Họ chấm |
|---|---|---|
| Live SQL (HackerRank, CoderPad, hoặc chia sẻ màn hình) | 30–60 phút, 2–4 bài | Đúng, nói được suy nghĩ, xử lý NULL/trùng/biên |
| Câu hỏi dbt / mô hình nói miệng | 30–45 phút | Hiểu sâu vì sao, không chỉ cú pháp |
| Đọc / review code (cho một model dbt có lỗi) | 20–30 phút | Tìm bug, đề xuất cải thiện, ưu tiên |
| Take-home + đọc lại bài | 4–8 giờ + 45 phút | Xem [18.5](05-take-home.md) |
| System design | 45–60 phút | Xem tuần 16 |

## Live SQL: quy trình 5 bước mỗi bài

1. **Nhắc lại đề + hỏi grain:** "Bảng orders 1 dòng / đơn đúng không? Có đơn huỷ không? customer_id có NULL không?"
2. **Viết ví dụ nhỏ** 3–4 dòng input → output mong đợi (nói ra).
3. **Viết theo CTE từng bước**, đặt tên CTE theo ý nghĩa.
4. **Kiểm tra biên:** NULL, trùng, ngày trống, chia cho 0, hoà (tie) khi xếp hạng.
5. **Nói độ phức tạp / cách tối ưu** nếu bảng lớn (partition, lọc sớm).

## 15 dạng bài hay gặp (luyện đủ trước tuần 18)

| # | Dạng | Kỹ thuật | Đã luyện ở |
|---|---|---|---|
| 1 | Top N mỗi nhóm | `row_number()` / `qualify`, xử lý hoà bằng `rank`/`dense_rank` | practice_window_function |
| 2 | Luỹ kế, trung bình trượt | `sum() over (order by … rows between …)` | practice_window_function |
| 3 | So với kỳ trước (MoM, YoY) | `lag()`, join theo kỳ | |
| 4 | Gaps & islands (chuỗi ngày liên tiếp) | `date - row_number()` | |
| 5 | Retention theo cohort | cohort = tháng đầu, `datediff` tháng, pivot | |
| 6 | Phễu chuyển đổi | điều kiện theo thứ tự thời gian, `min(case when …)` | |
| 7 | Sessionization | khoảng cách > 30 phút → phiên mới, `sum(flag) over` | |
| 8 | Dedupe bản ghi mới nhất | `qualify row_number() over (partition by id order by updated_at desc) = 1` | take-home (CDC) |
| 9 | Snapshot dày đặc từ sự kiện | spine ngày × thực thể + luỹ kế / forward-fill | take-home, GĐ2 K9 |
| 10 | SCD2 từ snapshot hằng ngày | `lag` so sánh thuộc tính, `lead` cho valid_to | GĐ1, GĐ2 K4 |
| 11 | Khách mua lại trong N ngày | self-join hoặc `lead` | |
| 12 | Tỉ lệ / tỉ trọng | `x / sum(x) over ()`, ép kiểu số thực | |
| 13 | Pivot / unpivot | `sum(case when …)`, `PIVOT` | |
| 14 | Median / percentile | `percentile_cont`, `median` | |
| 15 | Đối soát 2 bảng | `full outer join` theo khoá + so tổng, `EXCEPT` hai chiều | take-home (GL) |

Mẹo: luyện trên **DuckDB** (nhanh), nhưng biết cú pháp khác của Snowflake/BigQuery/Postgres (`qualify` không có ở Postgres; `date_diff` vs `datediff`; `safe_divide` của BigQuery).

## Câu hỏi dbt nói miệng: trả lời kiểu Mid

Đừng chỉ định nghĩa. Trả lời theo **định nghĩa → khi nào dùng → bẫy → ví dụ của bạn**.

> **"Incremental model hoạt động thế nào?"**
> *"Lần đầu dbt tạo cả bảng. Các lần sau chỉ chạy phần trong `is_incremental()`, thường lọc dữ liệu mới hơn `max(updated_at)` trong bảng đích, rồi merge hoặc delete+insert theo `unique_key`. Em dùng khi bảng lớn và tăng đều. Bẫy thứ nhất là dữ liệu đến trễ: lọc cứng theo max sẽ bỏ sót, nên em thêm lookback vài ngày. Bẫy thứ hai là thêm cột với `on_schema_change` mặc định `ignore` thì cột mới không vào bảng. Trong lab em gặp đúng bẫy dữ liệu trễ: sự kiện ngày 3 có event_ts của ngày 1, em sửa bằng lookback và kiểm chứng bằng replay 12 ngày."*

Chuẩn bị theo cách đó cho: snapshot, macros/Jinja, tests (generic/singular/unit), sources/freshness, contracts/versions, state/slim CI, packages, materializations, semantic layer, exposures.

## Đọc code: bài tập mẫu

Tìm ít nhất 6 vấn đề trong model sau (đáp án bên dưới):

```sql
-- models/marts/fct_revenue_daily.sql
{{ config(materialized='incremental') }}
select
    date(o.created_at) as day,
    sum(o.total_amount) as revenue,
    count(*) as orders,
    avg(o.total_amount) as aov
from {{ source('shop', 'orders') }} o
left join {{ source('shop', 'order_items') }} i on i.order_id = o.order_id
where o.status != 'cancelled'
{% if is_incremental() %}
  and o.created_at > (select max(day) from {{ this }})
{% endif %}
group by 1
```

<details><summary>Đáp án</summary>

1. Mart đọc thẳng `source()`: bỏ qua tầng staging.
2. Join `order_items` rồi `sum(total_amount)` và `count(*)`: **fan-out**, doanh thu và số đơn bị nhân theo số dòng hàng.
3. `status != 'cancelled'` loại luôn dòng `status` NULL (NULL không thoả `!=`).
4. `date(created_at)`: múi giờ (UTC vs giờ VN) có thể gán sai ngày.
5. Incremental không có `unique_key` → append. Chạy lại cùng ngày sẽ trùng dòng, và ngày hôm nay chưa trọn vẹn sẽ bị cộng dồn sai.
6. `created_at > max(day)`: so timestamp với ngày → lấy lại gần trọn ngày cuối (cộng với điểm 5 là ra dòng trùng); và **không có lookback** cho đơn đổi trạng thái (huỷ) sau đó → doanh thu ngày cũ không bao giờ được cập nhật.
7. `aov` lưu sẵn trong bảng ngày: không gom lên tuần/tháng được (nên để semantic layer tính ratio).
8. Không test, không description, grain không ghi ở đâu.
</details>
