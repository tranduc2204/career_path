# Bài take-home mẫu: "Ngân hàng số Sen" (Analytics Engineer, Mid)

> Dùng ở **tuần 18–20** của GĐ5. Đề viết giống email một công ty gửi thật. Làm trong **một buổi, tối đa 6 giờ**, bấm giờ, rồi tự chấm: phần khách quan bằng `scripts/check.py`, phần chủ quan bằng rubric cuối file.
> Đã kiểm chứng 07/11/2026: lời giải mẫu trong `dap-an/` đạt 5/5 phần khách quan; 3 kiểu lời giải "ngây thơ" (không áp CDC đúng, không forward-fill tỷ giá, tính số dư chỉ từ đầu kỳ) đều bị bộ chấm bắt.
> Cùng bối cảnh với đề system design [3. Transformation layer cho ngân hàng](../GD5-phong-van/tuan-16-system-design/03-de-ngan-hang-transformation-layer.md). Làm đề system design trước để có khung, rồi làm bài này để biến khung thành code.

---

## Email của nhà tuyển dụng

> **Tiêu đề:** [Sen Bank] Bài tập kỹ thuật vị trí Analytics Engineer
>
> Chào bạn,
>
> Cảm ơn bạn đã tham gia vòng 2. Đội Data Platform của Sen Bank đang xây tầng transformation cho báo cáo tài chính. Chúng tôi gửi bạn một bản trích dữ liệu đã ẩn danh (DuckDB) và mong bạn dựng một dbt project nhỏ.
>
> **Thời gian:** bạn tự sắp xếp, nhưng chúng tôi mong bạn không dành quá 6 giờ. Chỗ nào chưa kịp làm, hãy ghi lại cách bạn sẽ làm.
>
> **Dữ liệu** (`takehome.duckdb`):
> - `core.customers`, `core.accounts`: trạng thái hiện tại.
> - `core.txn_cdc`: **nhật ký CDC** của bảng giao dịch, lấy từ Debezium. `op`: `r` snapshot ban đầu, `c` tạo, `u` sửa (after-image), `d` xoá. `lsn` tăng dần. Connector đôi khi gửi lại sự kiện cũ.
> - `ref.fx_rates`: tỷ giá USD→VND, chỉ niêm yết ngày làm việc.
> - `gl.daily_balances`: số dư sổ cái (GL) cuối ngày theo sản phẩm × loại tiền.
>
> **Yêu cầu.** Kỳ báo cáo: **01/11/2026 → 31/01/2027** (`var('as_of_date')`).
>
> 1. `fct_transactions`: một dòng cho mỗi giao dịch **đang có hiệu lực** (đã ghi sổ, chưa bị đảo, chưa bị xoá), theo trạng thái mới nhất. Cột: `txn_id, account_id, customer_id, value_date, amount, currency, amount_vnd, txn_type, channel`. `amount_vnd` dùng tỷ giá của `value_date`.
> 2. `fct_account_daily_balance`: số dư cuối ngày của **mỗi tài khoản, mỗi ngày** tài khoản còn mở trong kỳ báo cáo (kể cả ngày không có giao dịch). Cột: `account_id, balance_date, balance, balance_vnd`.
> 3. `rpt_gl_reconciliation`: đối soát tổng số dư tài khoản với GL theo ngày × sản phẩm × loại tiền. Cột: `balance_date, product, currency, total_account_balance, gl_balance, difference, is_matched`. Nếu có chỗ lệch, hãy cho chúng tôi biết bạn nghĩ nguyên nhân là gì.
> 4. `mart_customer_monthly`: mỗi khách, mỗi tháng (có ít nhất một tài khoản mở): `customer_id, month_start, total_inflow_vnd, total_outflow_vnd, txn_count, avg_daily_balance_vnd, is_active`. Khách "hoạt động" nếu có giao dịch do **chính khách** thực hiện trong tháng.
>
> **Nộp:** repo (hoặc zip) gồm dbt project chạy được bằng `dbt build`, test bạn thấy cần thiết, và một `README.md` ngắn: **giả định**, **quyết định thiết kế**, **việc bạn sẽ làm tiếp theo** nếu có thêm thời gian. Vòng sau chúng tôi sẽ cùng bạn đọc lại bài trong 45 phút.
>
> Chúc bạn làm bài vui!

---

## Chuẩn bị

```bash
cd ~/Desktop/target_ae/bai-tap-take-home
uv sync && source .venv/bin/activate
cd lab && export DBT_PROFILES_DIR=.
python scripts/generate.py          # tạo takehome.duckdb (tất định, chạy lại lúc nào cũng ra y hệt)
```

`lab/` chỉ có `dbt_project.yml`, `profiles.yml` và folder trống: giống thật, bạn tự dựng mọi thứ. Được dùng `dbt_utils` và mọi tài liệu (công ty thật cũng cho phép), nhưng **tự viết**, đừng mở `dap-an/`.

Bấm giờ. Gợi ý phân bổ 6 giờ:

| Thời gian | Việc |
|---|---|
| 0:00–0:45 | **Khảo sát dữ liệu** bằng SQL: grain, op, trùng lsn, ngày giờ, tỷ giá, đóng tài khoản. Ghi giả định ngay khi phát hiện |
| 0:45–1:00 | Vẽ DAG trên giấy: staging → intermediate → 4 mart |
| 1:00–3:30 | Viết model theo thứ tự 1 → 2 → 3 → 4. **Dùng bảng 3 để tự kiểm tra bảng 1 và 2** |
| 3:30–4:30 | Test, description, sources |
| 4:30–5:30 | README: giả định, quyết định, phát hiện, việc tiếp theo |
| 5:30–6:00 | Chạy lại từ đầu (`dbt build` trên DB mới), đọc lại như người chấm |

Xong (hoặc hết giờ):

```bash
dbt build
python scripts/check.py      # 5 phần khách quan
```

## Bộ chấm khách quan kiểm tra gì

| # | Kiểm | Bẫy |
|---|---|---|
| 1 | `fct_transactions` từng dòng, từng cột | Sự kiện phát lại; nhiều sự kiện / giao dịch; `u` sửa số tiền; `u` đảo giao dịch; `d`; ngày nghiệp vụ vs giờ UTC; tỷ giá cuối tuần / ngày lễ; VND không có trong bảng tỷ giá |
| 2 | `fct_account_daily_balance` từng dòng | Bảng phải dày đặc; số dư luỹ kế từ **ngày mở tài khoản** (có từ trước kỳ báo cáo, nằm trong snapshot `r`); tài khoản đã đóng dừng ở `close_date` |
| 3 | `rpt_gl_reconciliation` | Đúng **1** dòng lệch. Lệch nhiều hơn nghĩa là bảng 1/2 của bạn sai, không phải GL sai |
| 4 | `mart_customer_monthly` | Số dư là **semi-additive** (trung bình theo ngày của tổng, không phải tổng của trung bình); lãi/lương do hệ thống tạo không tính là hoạt động |
| 5 | Có `sources`, test khoá cho 4 mart, description cho mọi model, README có 3 mục | |

## Rubric chủ quan (người phỏng vấn chấm gì)

Tự chấm 1–4 cho mỗi dòng. Mid cần trung bình ≥ 3; điểm 4 ở 2–3 dòng là thứ làm bạn nổi bật.

| Tiêu chí | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| **Đúng** | Sai số liệu chính | Đúng phần lớn, lệch ở bẫy | Đúng hết (5/5) | Đúng + tự phát hiện, giải thích dòng lệch GL |
| **Cấu trúc** | 1–2 file SQL khổng lồ | Có tầng nhưng lẫn lộn | staging / intermediate / marts rõ, tên theo chuẩn | + logic khó tách thành model trung gian có tên nói lên ý nghĩa |
| **Test** | Không có | `unique`/`not_null` lèo tèo | Khoá mọi mart, relationships, accepted_values cho `op` | + test nghiệp vụ (đối soát warn, số dư tài khoản đóng = 0), unit test logic chọn lsn |
| **Đọc được** | Không ai đọc nổi | CTE đặt tên tuỳ tiện | CTE theo bước, comment chỗ khó | Người lạ đọc 5 phút là hiểu grain + bẫy |
| **README** | Không có / chỉ lệnh chạy | Liệt kê việc đã làm | Giả định + quyết định + việc tiếp theo | + đánh đổi có lý do (table vs incremental, khi nào full refresh), phát hiện về dữ liệu |
| **Tư duy production** | Không nhắc | Nhắc chung chung | Incremental + lookback cho ghi sổ lùi, freshness CDC | + chi phí, PII, snapshot `accounts`, lịch chạy theo giờ khoá sổ |

## Vòng "đọc lại bài" 45 phút: câu hỏi hay gặp

1. Nếu `txn_cdc` có 2 tỷ dòng, model nào của bạn sẽ chậm nhất? Bạn chuyển sang incremental thế nào mà vẫn đúng với giao dịch ghi sổ lùi 3 ngày và sự kiện `u` đến sau 4 ngày?
2. GL lệch ngày 15/01. Bạn báo cho ai, bằng câu chữ gì? Bạn có "sửa" số dư cho khớp không?
3. Vì sao không dùng `booking_ts` làm ngày nghiệp vụ? Cho một ví dụ cụ thể trong dữ liệu.
4. `core.accounts` là trạng thái hiện tại. Nếu khách đổi sản phẩm (CASA → SAVING), báo cáo tháng trước bị gì? Bạn đề xuất gì?
5. Kiểm toán hỏi "số dư ngày 30/11 mà bạn báo lúc 01/12 là bao nhiêu?" (khác số hiện tại vì có ghi sổ lùi ngày). Mô hình của bạn trả lời được không? Cần thêm gì? (gợi ý: lưu snapshot báo cáo, bitemporal)
6. Bạn sẽ đặt contract và quyền truy cập thế nào cho 4 bảng này?

## Sau khi làm

- So với `dap-an/` (đọc cả README của lời giải). Ghi 3 điều bạn làm tốt hơn và 3 điều kém hơn.
- Làm lại câu 1 và câu 5 ở trên **bằng code**: incremental cho `fct_account_daily_balance` + một bảng `rpt_balance_as_reported` lưu số đã báo cáo.
- Đưa bài lên GitHub như một project portfolio nhỏ ("CDC → số dư ngày → đối soát GL"). Nhà tuyển dụng ngân hàng rất thích đọc đúng những thứ này.
