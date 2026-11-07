# 16.2 Thư viện mẫu thiết kế (dùng lại cho mọi đề)

> Mỗi mẫu có: **khi nào dùng**, **các phương án**, **đánh đổi**, và **câu nói gọn** để dùng trong phỏng vấn. Các đề 3–10 lắp ghép từ những mẫu này. Đây là "từ vựng" của bạn.

## A. Lấy dữ liệu (ingest)

| Mẫu | Khi nào | Đánh đổi |
|---|---|---|
| **Full extract hằng ngày** | Bảng nhỏ (< vài triệu dòng), nguồn không có `updated_at` | Đơn giản, có lịch sử nếu giữ từng file. Tốn băng thông, trễ 1 ngày |
| **Incremental theo `updated_at`** | Nguồn có cột cập nhật đáng tin | Không thấy **xoá cứng**; nhạy với đồng hồ lệch, cập nhật không bump `updated_at` (lab GĐ1 ngày 3) |
| **CDC từ log** (Debezium, GoldenGate, Fivetran HVR, Datastream) | OLTP lớn, cần mọi thay đổi kể cả xoá, độ trễ phút | Đúng và đủ nhất. Cần quyền đọc log, vận hành connector, xử lý `r/c/u/d`, phát lại, thứ tự |
| **Event / stream** (Kafka, Pub/Sub) | Sự kiện sinh ra ở app (click, giao dịch thẻ) | Gần real-time. Trùng, sai thứ tự, schema drift, cần schema registry |
| **API / SaaS connector** (Fivetran, Airbyte, dlt) | Nguồn SaaS (CRM, quảng cáo) | Nhanh. Phụ thuộc rate limit, giới hạn lịch sử của API |
| **File thả** (SFTP, S3) | Đối tác, ngân hàng đối tác, cơ quan nhà nước | Định dạng hay đổi; phải có contract file + kiểm tra số dòng / checksum |

**Câu nói gọn:** "Với core banking em chọn CDC vì cần cả sửa và xoá, và đối soát cần đầy đủ từng thay đổi. Tầng raw giữ nguyên nhật ký CDC (append-only, không bao giờ sửa), mọi diễn giải làm ở dbt để chạy lại được."

## B. Phân tầng

```
raw / landing  ─▶ staging ─▶ (vault | intermediate) ─▶ marts ─▶ semantic / exposures
bất biến, đúng     1-1 với     tích hợp nhiều nguồn,        star schema    metric, quyền
như nguồn          nguồn,      logic nghiệp vụ, lịch sử      theo domain    truy cập BI
                   hard rules
```

| Quyết định | Phương án | Chọn khi |
|---|---|---|
| Có giữ raw bất biến không? | Có (append-only, partition theo ngày nạp) | **Luôn có**, nhất là tài chính: chạy lại / kiểm toán / debug |
| Tầng tích hợp | Kimball trực tiếp vs **Data Vault** vs intermediate dbt thường | Vault khi nhiều nguồn chồng lấn, nguồn đổi thường xuyên, yêu cầu audit lịch sử mạnh (ngân hàng). Kimball/intermediate khi ít nguồn, đội nhỏ (ADR ở GĐ2) |
| Persistent staging | Lưu mọi phiên bản dòng nguồn (snapshot / ma trận CDC) | Khi nguồn chỉ có trạng thái hiện tại mà vẫn cần lịch sử |

## C. Mô hình hoá

| Mẫu | Ghi nhớ |
|---|---|
| **Grain trước, cột sau** | Mỗi fact: "1 dòng / ___". Mọi cột phải đúng grain đó |
| **Transaction fact** | Sự kiện bất biến (giao dịch, đơn). Additive |
| **Periodic snapshot** | Trạng thái theo kỳ (số dư ngày). **Semi-additive**: cộng theo thực thể, không cộng theo thời gian |
| **Accumulating snapshot** | Quy trình có mốc (đơn vay: nộp → duyệt → giải ngân → tất toán) |
| **Factless** | Sự kiện không số đo / coverage |
| **SCD2** | Lịch sử thuộc tính chiều. Dựng từ CDC/snapshot. Khoá ổn định (durable key) + surrogate key theo phiên bản |
| **Bitemporal** | 2 trục thời gian: **valid time** (sự việc đúng khi nào) và **transaction time** (hệ thống biết khi nào). Cần cho "số đã báo cáo lúc đó là bao nhiêu" |
| **Conformed dimension** | Một `dim_customer`, `dim_date`, `dim_branch` dùng chung cho mọi fact |
| **Bridge** | Nhiều–nhiều (khách đồng sở hữu tài khoản) |

## D. Thời gian và dữ liệu trễ

| Tình huống | Mẫu xử lý |
|---|---|
| Sự kiện đến muộn vài ngày | Incremental với **lookback** (xử lý lại N ngày gần nhất) hoặc microbatch `lookback` |
| Sửa / xoá ở nguồn (CDC) | `merge` theo khoá trên bảng "current state"; giữ log để dựng lại |
| Ghi sổ lùi ngày (backdated) | Số dư quá khứ thay đổi → snapshot phải tính lại từ ngày bị ảnh hưởng (`min(value_date)` trong lô mới) |
| Kỳ đã khoá sổ | **Không sửa số đã báo cáo**. Ghi điều chỉnh vào kỳ hiện tại, hoặc lưu bảng "as reported" tách bản "restated" |
| Múi giờ | Lưu UTC, **ngày nghiệp vụ** là cột riêng (value_date / business_date theo giờ địa phương) |
| Chiều đến sau fact | Inferred member / thành viên `-1` rồi cập nhật (GĐ2) |

**Câu nói gọn:** "Em tách *khi nào sự việc xảy ra* (value_date) và *khi nào kho biết* (loaded_at). Số dư dựa trên value_date; incremental dựa trên loaded_at với lookback; báo cáo đã nộp thì lưu bản chụp."

## E. Tính idempotent và backfill

- Mọi model chạy lại cùng đầu vào phải ra **cùng kết quả**. Không dùng `current_date` trong logic. Truyền ngày chạy qua `var` / `event_time`.
- Incremental phải **xoá rồi chèn** (hoặc merge) theo cửa sổ, không append mù.
- Backfill = chạy lại một khoảng ngày bằng `--event-time-start/end` (microbatch) hoặc `--vars`, không cần sửa code.
- Full refresh định kỳ (tuần/tháng) để chặn sai lệch tích luỹ của incremental.

## F. Chất lượng dữ liệu (chi tiết ở đề 4)

Ba lớp: **ngăn** (contract, test ở staging chặn lỗi luật), **phát hiện** (freshness, volume/anomaly, đối soát với nguồn/GL), **phản ứng** (severity, cảnh báo đến đúng chủ, runbook). Đối soát là "test vua" của dữ liệu tài chính: tổng của bạn phải khớp sổ cái.

## G. Môi trường và triển khai (chi tiết ở đề 5)

dev (schema cá nhân, `--empty`/`--sample`) → CI (schema theo PR, slim CI + defer) → (staging/UAT) → prod (deploy khi merge, artifact lưu lại, rollback). Blue-green bằng `dbt clone` / swap schema khi cần đổi lớn không gián đoạn.

## H. Bảo mật và tuân thủ

| Yêu cầu | Mẫu |
|---|---|
| PII | Gắn nhãn cột (`meta.pii`), masking policy / policy tag ở warehouse theo vai trò, dev dùng dữ liệu che |
| Phân quyền | RBAC theo domain (role `finance_reader`), row-level security cho chi nhánh / khu vực |
| Lưu trữ trong nước | Dữ liệu cá nhân của người Việt: chú ý quy định lưu trữ / chuyển dữ liệu ra nước ngoài (Luật An ninh mạng, Nghị định 53/2022, Luật BVDLCN 2025) → chọn vùng cloud, hoặc on-prem |
| Audit | Log truy cập của warehouse, lineage, giữ artifact mỗi lần chạy, không ai sửa tay bảng prod |
| Retention | Chính sách giữ / xoá (dữ liệu giao dịch ngân hàng thường phải giữ nhiều năm; dữ liệu marketing thì ngắn) |

## I. Chi phí

Đo trước (query tag / job label theo model, GĐ2 tuần 7), rồi mới tối ưu: incremental + partition/cluster, cỡ warehouse theo tải, tách warehouse ETL và BI, auto-suspend, giới hạn byte quét, aggregate cho dashboard nóng, xoá model không ai dùng (dựa vào exposures và query log).

## J. Tổ chức và ownership

| Quy mô | Mẫu |
|---|---|
| 1 đội, < 200 model | 1 repo, 1 project, groups theo domain |
| Nhiều đội, giao diện rõ | groups + access + contract + version; CODEOWNERS |
| Nhiều đội, tốc độ khác nhau, ranh giới rõ | **dbt Mesh**: nhiều project, model public làm giao diện (đề 8) |
| Metric dùng chung | semantic layer, chủ metric theo domain, metric "toàn công ty" có hội đồng duyệt (đề 7) |

## Bảng "nếu họ hỏi... thì nhắc tới..."

| Họ hỏi | Bạn nhắc |
|---|---|
| "Dữ liệu đến trễ?" | lookback, microbatch, khoá sổ, as-reported |
| "Nguồn đổi schema?" | contract với đội nguồn, schema_changes, staging phòng thủ, versions |
| "Số không khớp Finance?" | đối soát GL, định nghĩa metric ở semantic layer, chủ metric |
| "Chạy chậm / tốn tiền?" | đo theo model, incremental, partition/cluster, tách warehouse |
| "Đội mới vào?" | groups, access, docs, conventions, template project |
| "Ai được xem?" | PII tag, masking, RBAC, row-level security, audit |
| "Hỏng lúc 3 giờ sáng?" | severity, cảnh báo đúng chủ, runbook, dbt retry, idempotent |
