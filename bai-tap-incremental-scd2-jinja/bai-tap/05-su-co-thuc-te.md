# 05 — Sự cố thực tế (P1–P6): vận hành sau khi đã ổn định

> Đây là phần giống công việc thật nhất. Ở công ty, phần lớn thời gian của AE không phải viết model mới, mà là **giữ cho model cũ đúng** khi nguồn thay đổi không báo trước.

## Điều kiện bắt đầu

Bạn đã làm xong B, J, I, S và hệ thống "ổn định" ở ngày 5:

```bash
./scripts/replay.sh 5
dbt run -s fct_events_microbatch --event-time-start 2025-12-29 --event-time-end 2026-01-13
python scripts/check.py        # mọi bài B/J/I/S PASS (P1–P6 SKIP)
```

## Luật chơi

1. Mỗi lần `next` (ngày 6 → 11) là một buổi sáng đi làm. Script chỉ báo 🚨 có chuyện, **không nói chuyện gì**.
2. Bạn có trong tay đúng những gì một AE có: kết quả `dbt build` (lỗi, test đỏ, model bị SKIP), tin nhắn của người dùng (bên dưới), và quyền query dữ liệu.
3. Điều tra → sửa → `check.py` (bài P tương ứng, cùng các bài cũ) phải xanh lại.
4. Thao tác vận hành ngoài `dbt build` (backfill, chạy lại với tham số khác...) → ghi vào `scripts/hooks/after_day_<N>.sh`. `./scripts/replay.sh 11` phải xanh toàn bộ mà không cần làm tay.
5. Mỗi sự cố viết 1 postmortem ngắn (mẫu ở cuối) vào `lab/NOTES.md`.
6. Không xem `simulate.py status --reveal` trước khi đã điều tra ít nhất 20 phút.

Quy trình điều tra gợi ý cho mọi sự cố:

```
1. Cái gì đỏ/SKIP?            → đọc output dbt build, logs/dbt.log
2. Lỗi bắt đầu từ model nào?  → model gần nguồn nhất bị lỗi
3. Nguồn khác hôm qua ở đâu?  → describe raw.<bảng>; so sánh số dòng, giá trị, _loaded_at
4. Sửa ở tầng thấp nhất có thể → thường là staging
5. Dữ liệu đã nạp sai có tự lành không? → bảng incremental KHÔNG tự sửa dòng cũ
6. Lần sau phát hiện sớm bằng gì? → test, audit, alert
```

---

## P1 — Ngày 6 ⭐⭐

**Triệu chứng**
- `dbt build` báo 1 test đỏ ở staging, kéo theo nhiều model bị **SKIP**.
- 🗨️ PM: *"Dashboard hôm nay sao vẫn là số của hôm qua vậy em?"*

**Yêu cầu**
- Tìm nguyên nhân, sửa sao cho build xanh và `check.py P1` PASS.
- Trả lời: vì sao sửa ở staging chứ không sửa ở `fct_orders`?

**Câu hỏi postmortem**
1. Nếu 2 dòng trùng **không giống hệt nhau** (khác `_loaded_at` hoặc khác giá trị), bạn giữ dòng nào?
2. Test `unique` ở staging nên để `error` hay `warn`? Cân nhắc giữa "dashboard đứng yên" và "dashboard sai".

<details><summary>Gợi ý điều tra</summary>

```bash
dbt show --inline "select order_id, count(*) from raw.orders group by 1 having count(*) > 1"
dbt show --inline "select * from raw.orders where order_id in (select order_id from raw.orders group by 1 having count(*) > 1) order by order_id"
```
Ngoài thực tế: công ty dùng Fivetran/Airbyte/Kafka có cơ chế *at-least-once* — khi retry giữa chừng, cùng một dòng có thể bị ghi 2 lần.
</details>

<details><summary>Gợi ý sửa</summary>

`qualify row_number() over (partition by order_id order by _loaded_at desc) = 1` trong `stg_orders`.
</details>

---

## P2 — Ngày 7 ⭐⭐⭐

**Triệu chứng**
- `stg_orders` **ERROR**, khoảng 20 model và test phía sau bị SKIP.
- 🗨️ Kênh #data-alerts: *"dbt job 06:30 failed"*.

**Yêu cầu**
- Sửa **chỉ ở staging**, không đụng model nào khác.
- `./scripts/replay.sh 11` vẫn phải chạy được từ ngày 0 — tức là staging phải chạy đúng **cả trước và sau** thay đổi của nguồn.
- `check.py P2` PASS.

**Câu hỏi postmortem**
1. Có bao nhiêu model phía sau phải sửa? Điều này nói gì về giá trị của tầng staging?
2. Làm sao phát hiện **trước** khi job sáng bị lỗi? (gợi ý: test trên source như `dbt_expectations.expect_column_to_exist`, data contract với team backend, CI chạy trên dữ liệu staging của nguồn)
3. Nên hỗ trợ tên cũ bao lâu? Khi nào thì xoá nhánh xử lý tên cũ?

<details><summary>Gợi ý</summary>

So `describe raw.orders` hôm nay với hôm qua. Để hỗ trợ cả hai tên cột: `adapter.get_columns_in_relation(source('raw', 'orders'))` rồi `{% if ... %}` — giống cách bạn xử lý cột `channel` ở bài I7.
</details>

---

## P3 — Ngày 8 ⭐⭐⭐

**Triệu chứng**
- 1 test đỏ ở staging. Các model phía sau bị SKIP.
- 🗨️ Kế toán trưởng: *"Doanh thu ngày 29/12 trên dashboard cao hơn sổ sách. Từ hôm nay khách trả hàng được rồi, đơn trả hàng **không được tính doanh thu** nhé."*

**Yêu cầu**
- Cập nhật mọi chỗ liên quan để `check.py P3` PASS: test, var `order_statuses` (bài J3 phải có cột `orders_returned`), và **quy tắc doanh thu**: `fct_daily_revenue`, `customer_lifetime` không tính đơn `returned`.
- Nếu bạn đã đặt quy tắc ở `int_orders` (bài B7), bạn sửa mấy chỗ? Nếu không, bạn sửa mấy chỗ?

**Câu hỏi postmortem**
1. `accepted_values` đỏ đã chặn pipeline → dashboard đứng yên cả buổi sáng. Có nên đổi sang `warn`? Đổi thì mất gì?
2. Ai là người "sở hữu" định nghĩa doanh thu? Định nghĩa đó nên được ghi ở đâu để BI, finance, AE cùng dùng? (gợi ý: semantic layer — GĐ3 trong roadmap)
3. Các ngày cũ bị ảnh hưởng có tự được tính lại không? Vì sao (không)?

<details><summary>Gợi ý</summary>

`dbt show --inline "select order_status, count(*) from raw.orders group by 1"`. Đơn đổi sang trạng thái mới có `_loaded_at` mới → incremental tự nhặt được; bạn chỉ cần sửa logic và quy tắc.
</details>

---

## P4 — Ngày 9 ⭐⭐⭐⭐

**Triệu chứng**
- Nếu bạn làm bài I9: test `audit_fct_orders_vs_full` **đỏ**. Nếu không làm: **mọi thứ xanh**.
- 🗨️ Kế toán trưởng: *"Doanh thu 27/12 lệch sổ sách đúng $30. Bên backend bảo đã sửa dữ liệu từ hôm qua rồi mà?"*

**Yêu cầu**
- Tìm ra dữ liệu nào đã đổi và vì sao không model incremental nào thấy.
- Sửa số liệu bằng **backfill có chủ đích** (chỉ khoảng ngày bị ảnh hưởng, không full refresh cả kho), ghi thành `scripts/hooks/after_day_9.sh`.
- `check.py P4` PASS, và `./scripts/replay.sh 11` vẫn xanh.

**Câu hỏi postmortem**
1. Nếu bạn không làm bài I9, sự cố này được phát hiện bởi ai, sau bao lâu?
2. Liệt kê 3 cách phòng ngừa (gợi ý: test đối soát định kỳ; full refresh định kỳ hằng tuần cho bảng nhỏ; yêu cầu nguồn cập nhật `updated_at` bằng trigger hoặc dùng CDC).
3. Backfill theo `order_date` có rủi ro gì nếu sai khoảng ngày?

<details><summary>Gợi ý điều tra</summary>

So sánh `stg_orders` (view, luôn mới) với `fct_orders` (incremental):
```bash
dbt show --inline "select s.order_id, s.order_date, s.amount, f.amount as fct_amount, s._loaded_at from {{ ref('stg_orders') }} s join {{ ref('fct_orders') }} f using (order_id) where s.amount <> f.amount"
```
Nhìn cột `_loaded_at` của các dòng lệch.
</details>

<details><summary>Gợi ý sửa</summary>

Cho `fct_orders` và `fct_daily_revenue` nhận `--vars '{backfill_start: ..., backfill_end: ...}'`: khi có var thì lọc theo `order_date` thay vì watermark. Runbook gọi `dbt build -s fct_orders+ fct_daily_revenue+ --vars ...`.
</details>

---

## P5 — Ngày 10 ⭐⭐⭐⭐

**Triệu chứng**
- Một test đỏ ở staging (nếu bạn đã có `not_null` cho `stg_events.event_id`), hoặc `check.py I2` đỏ.
- 🗨️ Marketing: *"Số event ngày 2/1 bên mình thấp hơn Mixpanel 8 event. Mà sao có event không có ID?"*

**Yêu cầu**
- (a) Sự kiện không có `event_id` không được lọt vào các bảng sự kiện. Chọn: lọc ở staging, hay tách sang model "cách ly" (`stg_events__rejected`) để theo dõi số lượng? Ghi lý do.
- (b) Các sự kiện đến trễ hơn lookback phải có mặt trong `fct_events_by_ts`. Backfill một lần bằng runbook `scripts/hooks/after_day_10.sh` — **không** tăng lookback mặc định.
- (c) Thêm singular test phát hiện sự kiện bị bỏ sót: mọi `event_id` ở `stg_events` phải có trong `fct_events_by_ts`.
- `check.py P5` PASS.

**Câu hỏi postmortem**
1. Sửa staging xong, các dòng `event_id` NULL **đã nạp hôm qua** vào bảng incremental có tự biến mất không? Kiểm tra. Bạn dọn chúng thế nào?
2. Vì sao không tăng lookback lên 10 ngày cho mọi lần chạy?
3. `fct_events` (watermark theo `_loaded_at`) có bị mất 8 sự kiện trễ không? So với `fct_events_by_ts` — rút ra gì về việc chọn cột watermark?

<details><summary>Gợi ý</summary>

`dbt show --inline "select * from raw.events where event_id is null or event_id like 'ev_10_M%'"`. Chạy một lần: `dbt build -s fct_events_by_ts+ --vars '{lookback_days: 10}'`.
</details>

---

## P6 — Ngày 11 ⭐⭐⭐⭐

**Triệu chứng**
- **Không có gì đỏ.**
- 🗨️ QA lead: *"Hôm qua team QA tạo 2 đơn test trên production, backend đã đánh dấu xoá rồi mà sáng nay dashboard vẫn tính vào doanh thu?"*

**Yêu cầu**
- `stg_orders` có cột `is_deleted` (luôn có, `false` khi nguồn chưa có cột hoặc giá trị null).
- `fct_orders` có `is_deleted` đúng cho **mọi** đơn (giữ lại dòng, chỉ đánh dấu — để còn đối soát).
- Quy tắc doanh thu loại đơn `is_deleted` (`fct_daily_revenue`, `customer_lifetime`).
- `check.py P6` PASS và `./scripts/replay.sh 11` xanh.

**Câu hỏi postmortem**
1. Cột mới thêm vào `fct_orders` bằng `append_new_columns` có giá trị gì ở các dòng cũ? Vì sao `check.py P6` có thể vẫn đỏ dù 2 đơn test đã đúng? Sửa thế nào?
2. Soft delete và hard delete (khách 7, ngày 3): cách nào dễ xử lý hơn cho kho dữ liệu? Vì sao?
3. Nên lọc đơn đã xoá ở tầng nào: staging, intermediate hay mart?

<details><summary>Gợi ý</summary>

`describe raw.orders` → có cột mới. Trong `stg_orders`: `coalesce(_is_deleted, false) as is_deleted` khi cột tồn tại, ngược lại `false as is_deleted`. Quy tắc doanh thu ở `int_orders`: thêm `and not is_deleted`.
</details>

---

## Hoàn thành

```bash
./scripts/replay.sh 11
dbt run -s fct_events_microbatch --event-time-start 2025-12-29 --event-time-end 2026-01-13
python scripts/check.py        # 38/38 PASS
```

## Mẫu postmortem (ghi vào `lab/NOTES.md`)

```markdown
### P<n> — <tiêu đề ngắn>
- **Phát hiện lúc / bởi:** (test nào, người dùng nào)
- **Ảnh hưởng:** (model nào sai/đứng yên, bao lâu, ai bị ảnh hưởng)
- **Nguyên nhân gốc:** (thay đổi gì ở nguồn, vì sao pipeline không chịu được)
- **Cách sửa:** (code + thao tác vận hành, link runbook)
- **Phòng ngừa:** (test/alert/thoả thuận với nguồn để lần sau phát hiện sớm hoặc không xảy ra)
```

Đây là thứ đáng đưa vào portfolio và kể trong phỏng vấn hơn bất kỳ model nào: nhà tuyển dụng Mid/Senior hỏi *"kể một sự cố dữ liệu bạn đã xử lý"* gần như chắc chắn.
