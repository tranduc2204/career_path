# 02 — Incremental (I1–I9)

> Lý thuyết: [2.1 incremental](../../GD1-ly-thuyet/tuan-2/01-incremental-models.md) · [2.2 late-arriving & backfill](../../GD1-ly-thuyet/tuan-2/02-late-arriving-data-va-backfill.md)

Tất cả model đặt trong `models/marts/`. Quy trình chung: **viết model ở ngày 0 → `next` từng ngày → build → check**. Khi sửa logic: `dbt build -s <model> --full-refresh`.

Mẹo quan sát: mỗi lần build, xem log trong `logs/dbt.log` (tìm `merge into`, `delete from`, `insert into`) để thấy dbt thực sự chạy SQL gì cho từng chiến lược.

---

## I1 ⭐⭐ `append` — sự kiện

**Yêu cầu:** `fct_events_append` (event_id, user_id, event_type, event_ts, _loaded_at)
- `materialized='incremental'`, `incremental_strategy='append'`
- Lần sau chỉ lấy dòng có `_loaded_at` mới hơn `max(_loaded_at)` trong bảng.

**Làm:** build ở ngày 0 → `next` tới ngày 2 (build mỗi ngày).

**Kiểm tra:** `check.py I1` — PASS nghĩa là bảng có đúng số dòng của nguồn; đọc kỹ thông báo: có bao nhiêu dòng **trùng `event_id`**?

**Thử nghiệm**
1. Xoá khối `{% if is_incremental() %}` rồi build 2 lần liên tiếp. Chuyện gì xảy ra?
2. Build 2 lần trong cùng một ngày (không `next`) với filter đúng: có trùng không? Vì sao?

**Câu hỏi suy ngẫm:** Append đúng khi nào? Sự kiện bị gửi lại (at-least-once delivery) là chuyện bình thường hay hiếm trong thực tế?

---

## I2 ⭐⭐ Chống trùng sự kiện

**Yêu cầu:** `fct_events` (cùng cột với I1), **không có `event_id` trùng**, kể cả khi `--full-refresh` ở ngày 5.
- Có `unique_key='event_id'`, chiến lược `delete+insert` hoặc `merge`.
- Dedupe ngay trong batch.

**Kiểm tra:** `check.py I2` ở ngày ≥ 2. Rồi chạy `dbt build -s fct_events --full-refresh` ở ngày 5 và check lại.

**Câu hỏi suy ngẫm**
1. Có `unique_key` rồi, vì sao vẫn phải dedupe trong batch? (gợi ý: lúc full refresh ở ngày 5, nguồn chứa cả 2 bản của cùng một sự kiện trong **cùng một batch**)
2. Khi trùng, bạn giữ bản nạp đầu tiên hay cuối cùng? Có quan trọng không?

<details><summary>Gợi ý</summary>

```sql
qualify row_number() over (partition by event_id order by _loaded_at) = 1
```
</details>

---

## I3 ⭐⭐ `merge` — đơn hàng

**Yêu cầu:** `fct_orders`
- `incremental_strategy='merge'`, `unique_key='order_id'`
- Lấy mọi cột của `stg_orders` (gợi ý `dbt_utils.star`) + cột `days_to_last_update` (bài J9, có thể thêm sau).
- **Phiên bản đầu, cố ý dùng watermark theo `updated_at`:**
  ```sql
  where updated_at > (select max(updated_at) from {{ this }})
  ```
- Gắn test `unique`, `not_null` cho `order_id`, `is_positive` cho `amount`.

**Kiểm tra:** `check.py I3` ở ngày 0 và 1 → PASS. Trạng thái đơn đổi mỗi ngày mà vẫn đúng → merge đang update.

---

## I4 ⭐⭐⭐ Đơn đến muộn

**Làm:** `next` sang **ngày 2**, build, `check.py I3`.

**Bạn sẽ thấy:** FAIL, thiếu 3 đơn. Thông báo cho biết `order_date`, `updated_at`, `_loaded_at` của chúng.

**Yêu cầu**
1. Giải thích bằng lời (ghi vào comment đầu file): vì sao 3 đơn này bị bỏ qua?
2. Vì sao chúng sẽ **không bao giờ** tự quay lại, kể cả khi chạy thêm nhiều ngày? (gợi ý: trạng thái của chúng)
3. Sửa watermark cho đúng, `--full-refresh`, đi tiếp tới ngày 5. Ngày 5 có thêm đơn đến muộn — vẫn phải PASS.

**Câu hỏi suy ngẫm**
1. `updated_at` (thời gian ở nguồn) và `_loaded_at` (thời gian vào kho) khác nhau thế nào? Khi nào chỉ có `updated_at` thì làm sao?
2. Nếu nguồn không có cả `_loaded_at`, bạn còn cách nào? (→ I6)

---

## I5 ⭐⭐⭐ `delete+insert` — doanh thu theo ngày

**Yêu cầu:** `fct_daily_revenue`, 1 dòng mỗi `order_date`:

| Cột | Ý nghĩa |
|---|---|
| `order_date` | |
| `order_count` | số đơn **không** bị huỷ |
| `revenue` | tổng `amount` của đơn không bị huỷ (0 nếu không có) |
| `max_loaded_at` | `_loaded_at` lớn nhất của các đơn trong ngày — dùng làm watermark |

- `incremental_strategy='delete+insert'`, `unique_key='order_date'`.
- Mỗi lần chạy: tìm các **ngày bị ảnh hưởng** (có đơn mới hoặc đơn thay đổi) và tính lại các ngày đó.

**Kiểm tra:** `check.py I5` ở các ngày 2 (đơn đến muộn), 4 (đơn bị huỷ), 5.

**Bẫy:** cách "tự nhiên" là chỉ `group by` các đơn trong batch mới. Ở ngày 0–1 nó vẫn PASS (vì cả ngày cùng đổi trạng thái một lúc), nhưng ngày 2 sẽ FAIL. Hãy thử cách đó trước để thấy, rồi tìm lỗi.

**Câu hỏi suy ngẫm**
1. Vì sao ở đây `delete+insert` tự nhiên hơn `merge`?
2. Nếu dùng `merge` với `unique_key='order_date'` thì có sai không?
3. Bảng tổng hợp theo ngày có rủi ro gì mà bảng chi tiết (fct_orders) không có?

<details><summary>Gợi ý</summary>

Hai bước: CTE `affected_dates` = `select distinct order_date from stg_orders where _loaded_at > (select max(max_loaded_at) from {{ this }})`; rồi tổng hợp **toàn bộ** đơn có `order_date in (select order_date from affected_dates)`.
</details>

---

## I6 ⭐⭐⭐ Lookback theo event time

**Bối cảnh:** giả sử nguồn sự kiện **không có `_loaded_at` đáng tin**, chỉ có `event_ts`.

**Yêu cầu:** `fct_events_by_ts` (event_id, user_id, event_type, event_ts)
- Lọc incremental theo `event_ts` bằng macro `get_incremental_filter('event_ts')` (bài J7) — có lookback `var('lookback_days')`.
- `unique_key='event_id'` + dedupe.

**Thử nghiệm ở ngày 3** (có 6 sự kiện đến muộn mang `event_ts` ngày 01-01):
```bash
python scripts/simulate.py goto 2 && dbt build --exclude fct_events_microbatch
python scripts/simulate.py next
dbt build -s fct_events_by_ts --vars '{lookback_days: 0}'
python scripts/check.py I6       # FAIL
dbt build -s fct_events_by_ts --vars '{lookback_days: 3}'
python scripts/check.py I6       # PASS
```

**Câu hỏi suy ngẫm**
1. Lookback dài thì đổi lại cái gì? Chọn N dựa trên dữ liệu thế nào?
2. Vì sao lookback **bắt buộc** đi cùng `unique_key`?
3. Sự kiện đến muộn hơn N ngày thì sao? Có cách nào phát hiện không?

---

## I7 ⭐⭐⭐ `on_schema_change` — nguồn thêm cột

**Bối cảnh:** ở **ngày 4**, `raw.orders` thêm cột `channel`.

**Yêu cầu**
1. `stg_orders`: chỉ chọn `channel` khi nguồn có cột này (dùng `adapter.get_columns_in_relation` — xem Bonus cuối 01-jinja.md). Build ở ngày 0–3 phải không lỗi.
2. Thử lần lượt 4 cấu hình của `fct_orders` ở **ngày 4**. Trước mỗi lần thử: `./scripts/replay.sh 3 && python scripts/simulate.py next`, rồi `dbt build -s stg_orders fct_orders`.

   | # | Cấu hình | Điều bạn sẽ thấy (trên dbt-duckdb) |
   |---|---|---|
   | a | `merge` + `on_schema_change='ignore'` (mặc định) | Build **lỗi** `Binder Error: ... does not have a column with name "channel"` → pipeline dừng |
   | b | `delete+insert` + `ignore` | Build **thành công**, nhưng `fct_orders` **âm thầm không có** cột `channel` |
   | c | Sau (b), đổi sang `append_new_columns`, build lại **không** full refresh | Có cột `channel`, nhưng `check.py I7` **vẫn FAIL**: 6 đơn ngày 4 bị null |
   | d | `on_schema_change='fail'` | dbt báo rõ *"source and target schemas ... are out of sync"* |

3. Quay về `merge` + `append_new_columns`, làm cho `check.py I7` PASS.

**Câu hỏi suy ngẫm**
1. Ở (a), sau khi sửa config và chạy lại, đơn ngày 4 có bị mất không? Vì sao một lần chạy **lỗi** lại an toàn hơn một lần chạy **thành công sai** như (b)? (gợi ý: watermark `max(_loaded_at)` có tiến lên không)
2. Ở (c), vì sao đơn ngày 4 null? Có cách nào sửa mà không phải full refresh cả bảng?
3. Hành vi của `ignore` khác nhau giữa các chiến lược và adapter. Bạn rút ra quy tắc gì cho production? (gợi ý: đừng để mặc định)
4. `append_new_columns` vs `sync_all_columns` khác nhau ở đâu? Khi nào dùng cái nào?
5. Nếu `fct_orders` liệt kê cột tường minh thay vì `dbt_utils.star`, chuyện gì xảy ra ở ngày 4?

---

## I8 ⭐⭐⭐⭐ `microbatch`

**Yêu cầu:** `fct_events_microbatch` (event_id, user_id, event_type, event_ts)
```sql
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='event_ts',
    batch_size='day',
    begin='2025-12-29',
    lookback=2
) }}
```
- Không viết `is_incremental()`. Vẫn dedupe sự kiện trong model.
- Thêm `{{ config(event_time='event_ts') }}` vào `stg_events`.

**Cách chạy — luôn chỉ rõ khoảng ngày:**
```bash
dbt run -s fct_events_microbatch --event-time-start 2025-12-29 --event-time-end 2026-01-07
```
Lý do: dữ liệu giả lập nằm ở 12/2025–01/2026, còn microbatch mặc định chạy tới **thời điểm hiện tại thật** → hàng trăm batch rỗng. Đây cũng là lý do model này bị `--exclude` khỏi build hằng ngày.

**Thử nghiệm**
1. Xem log: mỗi batch là 1 câu `delete ... where event_ts >= X and event_ts < Y` + `insert`. Các batch chạy **song song**.
2. Mở `logs/dbt.log`, tìm `stg_events`: input của mỗi batch đã được lọc theo ngày.
3. Xoá `event_time` khỏi `stg_events`, chạy lại, xem log: mỗi batch đọc **toàn bộ** `stg_events`. Trên DuckDB kết quả vẫn đúng (adapter lọc lại lúc insert), nhưng tốn hơn rất nhiều trên bảng lớn — và đừng dựa vào hành vi riêng của từng adapter.
4. Backfill đúng 1 ngày: `--event-time-start 2026-01-01 --event-time-end 2026-01-02`.
5. Làm 1 batch lỗi (vd tạm thêm điều kiện chia cho 0 theo ngày), chạy, rồi sửa và `dbt retry`.

**Kiểm tra:** `check.py I8`.

**Câu hỏi suy ngẫm:** microbatch khác gì `delete+insert` + lookback tự viết (I6)? Ưu/nhược?

---

## I9 ⭐⭐⭐⭐ Bảo vệ & đối soát

**Yêu cầu**
1. **Chặn full refresh nhầm:** thêm `full_refresh=false` cho `fct_events`. Chạy `dbt build -s fct_events --full-refresh` và xác nhận trong log rằng bảng **không** bị dựng lại.
2. **Test đối soát:** singular test `tests/audit_fct_orders_vs_full.sql` so `fct_orders` với kết quả tính lại toàn bộ từ `stg_orders` (cột `order_id, order_status, amount`), dùng `except` theo **cả hai chiều**. Test phải trả 0 dòng.
   Kiểm chứng: tạm đổi `fct_orders` về watermark `updated_at`, `./scripts/replay.sh 2 -s +fct_orders+` → test này phải fail.
3. **Backfill bằng vars:** cho `fct_daily_revenue` nhận `--vars '{backfill_start: 2025-12-27, backfill_end: 2025-12-31}'` để tính lại đúng khoảng ngày đó, bỏ qua watermark.

**Kiểm tra:** `check.py I9`.

**Câu hỏi suy ngẫm**
1. Test đối soát kiểu này tốn bao nhiêu trên bảng 1 tỉ dòng? Bạn giới hạn nó thế nào?
2. `full_refresh=false` rồi thì khi *thật sự* cần dựng lại bảng, quy trình nên ra sao?
