# 16.3 Đề 1: Thiết kế tầng transformation cho một ngân hàng

> Đề "kinh điển" của roadmap. Giải mẫu đầy đủ theo khung 6 bước. Đọc **sau khi** tự làm một lần có bấm giờ (60 phút).
> Bài thực hành bằng code cùng bối cảnh: [bai-tap-take-home](../../bai-tap-take-home/README.md) (CDC → số dư ngày → đối soát GL).

## Đề

> *"Ngân hàng X đang có core banking, hệ thống thẻ, hệ thống cho vay và CRM. Họ muốn xây kho dữ liệu để phục vụ báo cáo quản trị, báo cáo cho cơ quan quản lý và phân tích khách hàng. Bạn thiết kế tầng transformation (từ dữ liệu thô đã vào kho tới các bảng cho người dùng). Bạn có 45 phút."*

---

## Bước 1: Làm rõ (8 phút)

Đoạn hội thoại mẫu. **Bạn** hỏi, **PV** (người phỏng vấn) trả lời:

| Bạn hỏi | PV trả lời (giả định) | Vì sao câu này quan trọng |
|---|---|---|
| Người dùng chính là ai, họ quyết định gì? | Ban giám đốc (KPI ngày), Tài chính (báo cáo tháng, khoá sổ), Quản lý rủi ro (nợ xấu), Khối bán lẻ (phân tích khách) | 4 nhóm, 4 nhịp độ khác nhau |
| Báo cáo gửi cơ quan quản lý có đi qua kho này không? | Có, một phần báo cáo cho NHNN, và phải giải trình được | → **tái lập được**, audit, khoá sổ |
| Dữ liệu vào kho bằng cách nào? | Core và cho vay: CDC (Oracle GoldenGate) vào raw. Thẻ: file hằng ngày từ switch. CRM: API hằng giờ | Ba kiểu nạp → ba kiểu xử lý |
| Quy mô? | 3 triệu khách, 5 triệu tài khoản, 8 triệu giao dịch/ngày, 500 nghìn khoản vay | → ước lượng |
| SLA? | KPI ngày trước 07:30. Core chạy EOD (end-of-day batch) xong khoảng 02:00–03:00. Báo cáo tháng chốt ngày làm việc thứ 3 | → orchestration theo sự kiện EOD |
| Có cần gần real-time không? | Khối vận hành muốn xem giao dịch trong ngày, trễ 15 phút được | → tách luồng intraday khỏi luồng chính |
| Warehouse? Có được dùng cloud nước ngoài không? | Snowflake vùng Singapore đang được cân nhắc, nhưng dữ liệu khách hàng phải tuân thủ quy định lưu trữ. Giả sử **on-prem hoặc cloud được phê duyệt** | → ràng buộc vùng, PII |
| Số đã báo cáo có được sửa không? | Không. Sai thì điều chỉnh ở kỳ sau và giải trình | → "as reported" vs "restated" |
| Đội ngũ? | 6 người dữ liệu, sẽ thành 3 đội domain | → ownership, groups, sau này Mesh |

**Chốt giả định trên bảng:**

```
Người dùng: BGĐ (07:30 hằng ngày), Tài chính (tháng, khoá sổ), Rủi ro (nợ), Bán lẻ (khách hàng)
Nguồn: core + loan (CDC), card (file ngày), CRM (API giờ)
Quy mô: 3M khách, 5M TK, 8M GD/ngày, 500k khoản vay
SLA: sau EOD (~03:00) → mart sẵn 07:00; intraday ≤ 15 phút cho vận hành (luồng riêng)
Ràng buộc: tái lập báo cáo, audit, PII, lưu trữ trong vùng được phép, số đã khoá không sửa
Warehouse: Snowflake (giả định), dbt Core, orchestrator có sẵn
```

**Yêu cầu chức năng (trả lời được):**
1. Số dư cuối ngày theo sản phẩm, chi nhánh, phân khúc khách (và đối soát khớp sổ cái).
2. Dòng tiền vào/ra, số giao dịch theo kênh.
3. Dư nợ, phân loại nợ theo số ngày quá hạn, tỷ lệ nợ xấu theo tháng.
4. Chân dung khách hàng 360: sản phẩm đang dùng, số dư trung bình, hoạt động.
5. Tái lập: "báo cáo tháng 11 đã nộp có số gì, tính từ dữ liệu nào".

**Phi chức năng:** đúng (khớp GL), đúng giờ (07:00), tái lập, bảo mật PII, chi phí kiểm soát được, mở rộng cho 3 đội.

## Bước 2: Ước lượng (3 phút)

| | Ước lượng | Hệ quả thiết kế |
|---|---|---|
| Giao dịch | 8M/ngày → ~3 tỷ/năm → ~100–150 GB nén/năm | Lưu trữ rẻ; **không** full refresh lịch sử → incremental + partition/cluster theo `value_date` |
| Số dư ngày | 5M TK × 365 = **1,8 tỷ dòng/năm** | Dày đặc 13–25 tháng gần nhất; cũ hơn lưu dạng khoảng hiệu lực hoặc tháng |
| Nhật ký CDC | Mỗi giao dịch 1–3 sự kiện + cập nhật số dư tài khoản ở core → 20–30M sự kiện/ngày | Raw append-only, partition theo ngày nạp, giữ ≥ thời hạn lưu trữ bắt buộc |
| Khoản vay | 500k × 365 = 180M dòng snapshot/năm | Thoải mái |
| Tính toán | `dbt build` hằng ngày: chủ yếu incremental, ước 20–40 phút trên warehouse M | Cửa sổ 03:00 → 07:00 là đủ, có chỗ chạy lại 1 lần nếu lỗi |

## Bước 3: Kiến trúc tổng thể (8 phút)

```
NGUỒN                 RAW (bất biến)              DBT                                                      NGƯỜI DÙNG
core  ──CDC──┐        raw_core.*_cdc   ─┐   staging      integration (raw vault)      business      marts (Kimball)        semantic
loan  ──CDC──┼──────▶ raw_loan.*_cdc   ─┼─▶ stg_* ─────▶ hub_customer, hub_account ─▶ vault: PIT, ─▶ dim_customer (SCD2) ─▶ metric:
card  ──file─┤        raw_card.*_file  ─┤   (dedupe,     hub_loan, link_*, sat_*      bridge,       dim_account, dim_branch   dư nợ, NPL,
CRM   ──API──┘        raw_crm.*        ─┘    cast,       (lịch sử đầy đủ, insert-only) quy tắc       fct_transaction           số dư TB...
                      ingest.sync_log         đổi tên)                                 nghiệp vụ    fct_account_daily_balance    │
                                                                                                    fct_loan_daily / _monthly   ▼
                                                                                                    rpt_regulatory_* (as-reported) BI, báo cáo NHNN,
                                                                                                    rpt_gl_reconciliation       sổ tay phân tích
  intraday (≤15'): raw CDC ─▶ dynamic table / incremental 15' ─▶ ops_intraday_transactions ─▶ màn hình vận hành (không dùng cho báo cáo chính thức)

  XUYÊN SUỐT: orchestrator (chờ EOD xong) · DQ (freshness, volume, đối soát GL) · catalog + lineage · RBAC + masking PII · CI/CD 3 môi trường · giám sát chi phí
```

Một câu cho mỗi tầng:

- **Raw bất biến:** không bao giờ sửa, nên mọi thứ phía sau chạy lại được và kiểm toán được.
- **Staging:** 1-1 với bảng nguồn, chỉ "hard rules" (kiểu, tên, loại bản phát lại CDC). Không logic nghiệp vụ.
- **Raw vault:** 4 nguồn cùng nói về khách, tài khoản, khoản vay → hub/link/sat tích hợp theo business key, giữ **toàn bộ lịch sử insert-only**, thêm nguồn mới không phá cấu trúc cũ. Phù hợp yêu cầu audit của ngân hàng (ADR GĐ2).
- **Business vault:** quy tắc nghiệp vụ dùng chung (phân loại nợ, quy đổi tỷ giá), PIT để dựng chiều theo ngày nhanh.
- **Marts Kimball:** star schema theo domain cho người dùng: dễ hiểu, nhanh.
- **Semantic layer:** một định nghĩa cho "dư nợ", "tỷ lệ nợ xấu", "số dư bình quân".
- **Luồng intraday tách riêng:** độ tươi 15 phút không được làm phức tạp luồng báo cáo chính thức.

> Nếu PV hỏi "sao không bỏ Data Vault cho đơn giản?": *"Với 6 người và 4 nguồn, Kimball thẳng từ staging vẫn làm được và rẻ hơn lúc đầu. Em chọn Vault vì 2 lý do của ngân hàng: audit lịch sử từng thay đổi, và nguồn mới (ví điện tử, đối tác) sẽ tới. Nếu đội chưa từng làm Vault, em sẽ bắt đầu bằng Kimball + snapshot/persistent staging, và ghi ADR để xem lại sau 6 tháng."* Nói được cả hai phía là điểm cộng.

## Bước 4: Đi sâu (18 phút). Chọn 4 chỗ khó

### 4.1 Từ nhật ký CDC tới "trạng thái hiện tại" và "lịch sử"

Raw: mỗi sự kiện có `op` (insert/update/delete hoặc r/c/u/d), `commit_scn`/`lsn`, `commit_ts` (UTC), before/after image.

```
stg_core__txn_cdc                 1 dòng / sự kiện (loại bản phát lại trùng lsn)
   │
   ├─▶ int_txn__current           1 dòng / txn_id: sự kiện lsn lớn nhất, bỏ op = d
   │      (merge incremental theo txn_id, chỉ xử lý sự kiện có loaded_at mới)
   │
   └─▶ sat_txn (vault)            1 dòng / txn_id / thay đổi (hashdiff), insert-only → lịch sử để audit
```

Các điểm phải nói:

- **Thứ tự** theo `lsn`/SCN, **không** theo `commit_ts` (nhiều sự kiện cùng giây, đồng hồ lệch).
- **Phát lại:** connector khởi động lại gửi lại sự kiện cũ → dedupe theo `lsn` ở staging.
- **Delete:** core banking hiếm khi xoá cứng giao dịch (thường là reversal), nhưng bảng tham chiếu thì có. Xử lý tường minh.
- **Snapshot ban đầu (`r`)** và **sự kiện sau** phải nối liền, không trùng không hở (kiểm tra bằng số dư khớp GL).
- **Bảng "số dư tài khoản" của core** cũng có thể CDC về. Dùng nó làm **nguồn đối soát** cho số dư tính từ giao dịch, không thay thế.

### 4.2 Bảng số dư ngày: periodic snapshot dày đặc, incremental đúng

`fct_account_daily_balance`: **1 dòng / tài khoản / ngày** tài khoản còn mở. Khoá `(account_id, balance_date)`. Semi-additive.

Hai cách dựng:

| | A. Lấy số dư EOD từ core (bảng balance snapshot của core) | B. Tính luỹ kế từ giao dịch |
|---|---|---|
| Đúng với sổ sách | ✅ đúng như core | phụ thuộc tính đúng mọi giao dịch |
| Có cho ngày quá khứ khi core sửa | ❌ nếu core không chụp lại | ✅ tính lại được |
| Chi phí | thấp | cao hơn (window function trên tỷ dòng) |
| Dùng | **nguồn chính cho báo cáo** | **kiểm tra chéo** + ngày core thiếu snapshot |

Đề xuất: dùng A làm số chính thức, B làm đối soát (lệch → cảnh báo). Nếu core không cung cấp A, dùng B với incremental:

```
mỗi ngày:
  affected_from = min(value_date) của các giao dịch mới nạp/sửa từ lần chạy trước  (thường = hôm qua, ghi sổ lùi → sớm hơn)
  xoá + dựng lại fct_account_daily_balance cho balance_date ≥ affected_from
       số dư(d) = số dư(affected_from - 1) + luỹ kế giao dịch từ affected_from tới d
  giới hạn: affected_from ≥ ngày khoá sổ gần nhất  (sửa trước kỳ khoá → quy trình điều chỉnh, không tự động)
```

Lưu ý triển khai: partition/cluster theo `balance_date`; tài khoản không phát sinh vẫn có dòng (dày đặc). Nếu 1,8 tỷ dòng/năm là quá nhiều: dày đặc 13 tháng, phần cũ hơn nén thành bảng khoảng hiệu lực `(account_id, valid_from, valid_to, balance)`, rồi mở rộng lại khi cần.

### 4.3 Khoá sổ, "as reported" và tái lập báo cáo

Ngân hàng không được để số tháng 11 đã nộp **thay đổi** khi giao dịch ghi lùi về tháng 11 xuất hiện tháng 12. Hai trục thời gian:

```
valid time        : giao dịch thuộc ngày nghiệp vụ nào (value_date)
transaction time  : kho biết lúc nào (loaded_at / batch_id)
```

Thiết kế:

- `rpt_regulatory_<tên>` có cột `reporting_period`, `run_id`, `generated_at`, `source_snapshot` (ngày dữ liệu dùng). Mỗi lần **nộp chính thức** thì ghi thêm (append) một bản, **không ghi đè**. Đây là bảng "as reported".
- Các mart thường luôn là "restated" (số đúng nhất hiện tại).
- `rpt_period_adjustments`: chênh lệch giữa as-reported và restated cho các kỳ đã khoá → Tài chính giải trình / điều chỉnh kỳ sau.
- Tái lập: vì raw bất biến + vault insert-only + mã dbt có tag release, có thể dựng lại đúng bảng tại thời điểm nộp (git tag + filter `loaded_at ≤ thời điểm nộp`).

### 4.4 Đối soát với sổ cái (GL)

"Test vua" của dữ liệu ngân hàng. Mỗi ngày:

```
rpt_gl_reconciliation: ngày × sản phẩm × loại tiền × chi nhánh
   tổng số dư tài khoản (từ kho)  vs  số dư tài khoản GL tương ứng (từ hệ thống kế toán)
   difference, tolerance (0 cho VND, 0,01 cho ngoại tệ), is_matched
rpt_recon_breaks: các dòng lệch + trạng thái xử lý (new / investigating / explained / fixed), người phụ trách
```

- Lệch là **cảnh báo** cho Tài chính, không phải lý do chặn mọi dashboard. Có ngoại lệ: báo cáo cơ quan quản lý **không được phát hành** khi còn break chưa giải thích (gate ở bước publish).
- Nguyên nhân hay gặp: giao dịch thiếu/trùng trong kho (lỗi của mình), GL hạch toán nhầm (lỗi phía kế toán), khác biệt thời điểm cắt sổ (cut-off), tỷ giá quy đổi khác nhau.
- Bài take-home cài đúng một dòng GL hạch toán nhầm để bạn luyện phân biệt "lỗi của mình" và "lỗi của nguồn".

### 4.5 (Nếu còn giờ) Nợ vay và phân loại nợ

- `fct_loan_daily`: 1 dòng / khoản vay / ngày: dư nợ gốc, lãi, số ngày quá hạn (DPD), nhóm nợ.
- Phân loại theo DPD: theo quy định phân loại nợ của NHNN (tham khảo Thông tư 11/2021/TT-NHNN: nhóm 1 < 10 ngày, nhóm 2 10–89, nhóm 3 90–179, nhóm 4 180–359, nhóm 5 ≥ 360; nhóm 3–5 là nợ xấu). Ngân hàng còn có quy tắc **chuyển nhóm theo khách** (một khoản quá hạn kéo các khoản khác của cùng khách). Đây là **business rule** đặt ở business vault, có test và chủ sở hữu là Khối rủi ro.
- Tỷ lệ nợ xấu là **ratio** ở semantic layer: Σ dư nợ nhóm 3–5 / Σ dư nợ, tính ở grain được hỏi.

## Bước 5: Vận hành (8 phút)

| Mảng | Thiết kế |
|---|---|
| **Lịch chạy** | Không cron cứng 03:00. Sensor chờ **tín hiệu EOD hoàn tất** của core (bảng trạng thái batch hoặc file cờ) + freshness của raw → chạy staging/vault → marts. Cửa sổ dự phòng tới 06:30. Quá 06:30 → cảnh báo SEV2, thông báo BGĐ trước 07:30 |
| **DQ** | Freshness theo sync log; volume anomaly trên giao dịch theo kênh; luật ở staging (số tiền ≠ 0, tiền tệ hợp lệ); **đối soát GL** mỗi ngày; số dư tài khoản đã đóng = 0; tổng phân loại nợ = tổng dư nợ |
| **Chủ sở hữu** | 3 group: Core & Tài chính, Rủi ro & Tín dụng, Khách hàng & Bán lẻ. Mỗi mart public có owner, contract, SLA trong `meta` |
| **Bảo mật** | PII (họ tên, CMND/CCCD, SĐT, địa chỉ) chỉ ở staging/vault có quyền hạn chế; mart public dùng khoá ẩn danh; masking policy theo role; row-level security theo chi nhánh cho người dùng chi nhánh; dev/CI dùng dữ liệu che hoặc tổng hợp |
| **Tuân thủ** | Lưu trữ trong vùng được phép; log truy cập; không ai sửa tay prod (mọi thay đổi qua PR + phê duyệt); giữ artifact mỗi lần chạy (`manifest`, `run_results`) cho kiểm toán |
| **CI/CD** | dev → CI (slim CI + defer, `--empty` cho model lớn) → UAT (Tài chính nghiệm thu số trên dữ liệu thật đã che) → prod. Ngân hàng thường cần **change approval** (CAB): tag release, deploy theo lịch, rollback = deploy tag trước + `dbt clone`/swap. Chi tiết ở đề 5 |
| **Sự cố** | Runbook cho: EOD trễ, break đối soát, CDC dừng, nguồn đổi schema. Backfill bằng `--event-time-start/end` |
| **Chi phí** | Warehouse riêng cho ETL (M, chạy 1 cửa sổ) và BI (S, auto-suspend); query tag theo model; dashboard nặng dùng aggregate + cache |

## Bước 6: Tổng kết (2 phút)

> *"Em thiết kế 5 tầng: raw bất biến từ CDC, staging chuẩn hoá, raw vault tích hợp 4 nguồn có lịch sử đầy đủ cho audit, rồi mart Kimball và semantic layer cho người dùng. Ba quyết định chính: (1) số dư ngày dựng incremental theo ngày bị ảnh hưởng nhỏ nhất, có đối soát GL mỗi ngày; (2) tách 'as reported' khỏi 'restated' để báo cáo đã nộp không bao giờ đổi; (3) lịch chạy theo tín hiệu EOD chứ không theo giờ cố định. Rủi ro lớn nhất là chất lượng CDC lúc đầu. Em giảm nó bằng đối soát GL và số dư core song song trong 2 tháng đầu trước khi tắt báo cáo cũ. Nếu có 6 tháng: thêm luồng intraday, tách 3 đội thành dbt Mesh, đưa metric rủi ro lên semantic layer."*

---

## Lộ trình triển khai (người phỏng vấn Senior rất thích hỏi)

| Giai đoạn | Thời gian | Phạm vi | Thành công là gì |
|---|---|---|---|
| v1 | 0–3 tháng | Core: khách, tài khoản, giao dịch, số dư ngày, đối soát GL; 5 KPI cho BGĐ | Số khớp GL 100% ngày trong 4 tuần liền; dashboard trước 07:30 |
| v2 | 3–6 tháng | Cho vay, phân loại nợ, báo cáo tháng (as-reported); thẻ | Tài chính tắt bảng tính Excel cũ của báo cáo tháng |
| v3 | 6–12 tháng | Customer 360, semantic layer, intraday, Mesh 3 đội | Thời gian trả lời câu hỏi ad-hoc từ ngày → giờ |

## Câu hỏi đào sâu hay gặp + ý trả lời

1. **"Giao dịch ghi lùi về tháng đã khoá sổ thì sao?"** → Không tự sửa kỳ đã khoá. Mart restated cập nhật, as-reported giữ nguyên, `rpt_period_adjustments` ghi chênh lệch, Tài chính quyết định điều chỉnh kỳ hiện tại. Incremental giới hạn `affected_from ≥ ngày khoá sổ`.
2. **"Một khách có 3 CIF ở 3 hệ thống, làm sao ra customer 360?"** → Same-as link trong vault (khớp theo CCCD/SĐT đã chuẩn hoá, có điểm tin cậy), master customer key; quy tắc khớp là business rule có chủ, có lịch sử thay đổi; không gộp tự động khi điểm thấp → hàng chờ cho đội vận hành dữ liệu.
3. **"Core đổi phiên bản, bảng giao dịch đổi cấu trúc?"** → Contract với đội core, staging phòng thủ, `schema_changes` cảnh báo, chạy song song bản cũ/mới trong UAT, satellite mới trong vault (không phá hub/link).
4. **"Tại sao không full refresh cho chắc?"** → Ước lượng: 3 tỷ dòng/năm, số dư 1,8 tỷ dòng/năm; full refresh hằng ngày tốn thời gian/tiền và không kịp cửa sổ 03:00–07:00. Full refresh **định kỳ** (hằng tháng sau khoá sổ) để chặn sai lệch tích luỹ.
5. **"Tỷ giá dùng tỷ giá nào?"** → Tỷ giá chính thức theo quy định nội bộ (cuối ngày của ngân hàng), forward-fill ngày nghỉ, lưu tỷ giá đã dùng cùng dòng số dư (để tái lập), đánh giá lại ngoại tệ là business rule của Tài chính.
6. **"Real-time dashboard cho vận hành thì sao?"** → Luồng riêng, độ tươi 15 phút, **không** dùng cho báo cáo chính thức, ghi rõ trên dashboard "số tạm tính". Công nghệ: dynamic table / materialized view / incremental 15 phút trên raw CDC (đề 10).
7. **"Làm sao biết model nào ảnh hưởng báo cáo NHNN trước khi sửa?"** → Exposure cho mỗi báo cáo, `dbt ls -s +exposure:...`, CODEOWNERS bắt buộc duyệt của Tài chính cho các model đó, test hồi quy số (so số kỳ đã khoá trước/sau thay đổi phải bằng nhau).
8. **"Ai được xem số dư của một khách cụ thể?"** → RBAC + row-level theo chi nhánh/khối; PII masking; truy cập dữ liệu khách cấp cá nhân phải có lý do và được log; analyst mặc định chỉ thấy dữ liệu tổng hợp hoặc khoá ẩn danh.
9. **"6 người, 3 tháng, bạn cắt gì?"** → Cắt intraday, customer 360, semantic layer. Giữ CDC → số dư → đối soát GL → 5 KPI. "Đúng và đáng tin cho một ít" hơn "nhiều mà không ai tin".
10. **"Đo thành công thế nào?"** → % ngày đúng SLA, số break đối soát chưa giải thích, % báo cáo tắt khỏi Excel, thời gian trả lời câu hỏi mới, chi phí/tháng.

## Mid và Senior trả lời khác nhau ở đâu

| Chủ đề | Mid (đạt) | Senior (nổi bật) |
|---|---|---|
| Kiến trúc | Đúng các tầng, nói được vì sao | Nói khi nào **không** cần tầng đó, lộ trình theo đội ngũ |
| Mô hình | Grain, SCD2, semi-additive, đối soát | Bitemporal, as-reported vs restated, master data, quy tắc chuyển nhóm nợ theo khách |
| Vận hành | Test, SLA, CI/CD | Lịch theo EOD, gate phát hành báo cáo, change management của ngân hàng, đo độ tin cậy |
| Tổ chức | Groups, owner | Ranh giới domain, khi nào Mesh, ai là chủ metric toàn ngân hàng |
| Rủi ro | Liệt kê | Định lượng + kế hoạch giảm (chạy song song, tiêu chí cắt chuyển) |

## Lỗi hay gặp với đề này

- Vẽ Kafka + Spark + streaming mọi thứ. Báo cáo ngân hàng là **batch T+1**, chỉ vận hành cần intraday.
- Không nhắc **đối soát GL**. Với ngân hàng đây gần như là lỗi loại.
- Dùng `booking_ts` hoặc `commit_ts` (UTC) làm ngày nghiệp vụ.
- Sửa số kỳ đã khoá sổ "cho đúng".
- Cộng số dư theo ngày (semi-additive) ra "tổng số dư tháng".
- Bỏ quên PII và quyền truy cập.

## Kịch bản 45 phút

| Phút | Việc | Trên bảng |
|---|---|---|
| 0–7 | Hỏi 8–10 câu, chốt giả định | Khung giả định + 5 yêu cầu chức năng |
| 7–10 | Ước lượng | 3 con số: giao dịch/năm, số dư/năm, cửa sổ chạy |
| 10–18 | Kiến trúc tổng thể | Sơ đồ 5 tầng + intraday + xuyên suốt |
| 18–36 | Đi sâu 4.1 → 4.4 (hỏi PV muốn sâu chỗ nào) | Grain các bảng chính, sơ đồ incremental, as-reported |
| 36–43 | Vận hành | Bảng 7 mảng |
| 43–45 | Tổng kết + lộ trình | 3 câu + v1/v2/v3 |

## Luyện thêm

- Làm lại đề với biến thể: **ví điện tử** (không có GL truyền thống, nhưng có sổ ví và đối soát với ngân hàng đối tác), **công ty chứng khoán** (giá cuối ngày, danh mục, T+2), **bảo hiểm** (hợp đồng, kỳ phí, bồi thường: accumulating snapshot).
- Làm [bai-tap-take-home](../../bai-tap-take-home/README.md), rồi trả lời câu 1 và 5 của phần "đọc lại bài" bằng code.
