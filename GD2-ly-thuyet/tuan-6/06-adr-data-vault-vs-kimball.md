# 6.6 ADR và so sánh Data Vault với Kimball

## ADR là gì

**Architecture Decision Record (ADR)**: một văn bản ngắn ghi lại **một** quyết định kiến trúc quan trọng: bối cảnh lúc đó, các phương án đã cân nhắc, quyết định, và hệ quả. Khái niệm do Michael Nygard phổ biến (2011).

Vì sao Mid/Senior phải biết viết ADR:
- 6 tháng sau không ai nhớ "vì sao mình chọn cái này". Người mới vào đọc ADR là hiểu.
- Buộc bạn **so sánh có số liệu** thay vì "em thấy cái này hay".
- Roadmap của bạn đặt mục tiêu khoảng 5 ADR trong portfolio: đó là bằng chứng bạn biết **ra quyết định**, thứ phân biệt Mid với Junior.

Nguyên tắc:
- **Một quyết định / một file**, ngắn (1–2 trang).
- Lưu cạnh code: `docs/adr/0001-<ten-quyet-dinh>.md`, đánh số tăng dần.
- **Không sửa** ADR đã chấp nhận. Quyết định đổi → viết ADR mới, ADR cũ đổi trạng thái thành *Superseded by 0007*.
- Viết cả các phương án **bị loại** và lý do loại.

## Mẫu ADR (tiếng Việt, theo Nygard + MADR rút gọn)

```markdown
# 0001. <Tiêu đề: một câu nêu quyết định>

- Trạng thái: Đề xuất | Chấp nhận | Thay thế bởi 000X | Bỏ
- Ngày: 2026-11-25
- Người quyết định: <tên>

## Bối cảnh
Vấn đề cần giải quyết là gì? Ràng buộc nào đang có (số nguồn, team, ngân sách, yêu cầu kiểm toán, công cụ)?
Viết sao cho người không có mặt hôm nay vẫn hiểu.

## Các phương án đã cân nhắc
1. <Phương án A>
2. <Phương án B>
3. <Phương án C>

## So sánh
| Tiêu chí | A | B | C |
|---|---|---|---|
| ... (có số đo nếu được) | | | |

## Quyết định
Chọn <X>, vì <2–3 lý do chính, dẫn chiếu số đo>.

## Hệ quả
- Được: ...
- Mất / chấp nhận đánh đổi: ...
- Việc phải làm tiếp: ...
- Khi nào xem lại quyết định này: <điều kiện cụ thể, vd "khi số nguồn > 5" hoặc "khi có yêu cầu kiểm toán">
```

## So sánh Data Vault và Kimball

| Tiêu chí | Kimball (star schema) | Data Vault 2.0 |
|---|---|---|
| Mục đích chính | **Hiển thị**: dễ hiểu, query nhanh cho BI | **Tích hợp & lưu trữ**: chịu thay đổi, kiểm toán |
| Đơn vị mô hình | Quy trình nghiệp vụ (fact) + dimension | Khái niệm kinh doanh (hub), quan hệ (link), ngữ cảnh (satellite) |
| Số bảng | Ít | Nhiều (lab: 22 vs 32 model) |
| Độ khó truy vấn | Thấp (1 fact + vài dimension) | Cao, cần information mart / PIT |
| Lịch sử | Theo thiết kế từng dimension (SCD1/2) | **Mọi** thuộc tính, mặc định |
| Thêm nguồn mới | Sửa dimension/fact, thống nhất quy tắc ngay | Thêm stage + satellite/link, không sửa bảng cũ |
| Quy tắc nghiệp vụ đổi | Thường phải dựng lại dimension/fact | Chỉ tính lại business vault + mart |
| Kiểm toán, truy vết | Hạn chế | Mạnh (`RECORD_SOURCE`, `LOAD_DATETIME`, insert-only) |
| Nạp song song | Dimension trước, fact sau | Song song nhờ hash key |
| Dựng lại từ đầu | Được, **nếu nguồn giữ lịch sử** (hoặc có snapshot) | Phần chụp từ nguồn ghi đè: **không** (chỉ tồn tại nếu vault chạy đều) |
| Kỹ năng & công cụ | Phổ biến, dễ tuyển | Cần kỷ luật, cần automate_dv / datavault4dbt |
| Chi phí ban đầu | Thấp | Cao (thêm 1 tầng) |
| Hợp với | Team nhỏ, ít nguồn, cần giá trị nhanh | Doanh nghiệp nhiều nguồn, ngành có quy định (ngân hàng, bảo hiểm) |

### Không phải "chọn một"

| Kiến trúc | Mô tả | Khi nào |
|---|---|---|
| Kimball thuần | staging → marts | Đa số startup, team AE nhỏ, ≤ 3–4 nguồn |
| **Lai** | staging → raw vault cho **vài thực thể lõi** (khách, sản phẩm) → marts Kimball | Một số thực thể có nhiều nguồn, cần lịch sử đầy đủ; phần còn lại vẫn Kimball |
| Data Vault đầy đủ | staging → raw vault → business vault → information marts | Tổ chức lớn, nhiều team, kiểm toán chặt |

## Viết ADR với số liệu từ lab

Bài ADR ở [file 05 của lab](../../bai-tap-kimball-data-vault/bai-tap/05-data-vault-business-vault-va-mart.md) yêu cầu đo 4 thứ. Ví dụ phần "So sánh" của một ADR tốt:

| Tiêu chí | Kimball | Data Vault + mart | Nguồn số liệu |
|---|---|---|---|
| Số model cho cùng dữ liệu | 22 | 32 | `dbt ls ... \| wc -l` |
| Số bảng phải đọc để dựng `fct_sales` | 4 staging + 4 dim | 9 | đếm trong SQL |
| Dựng lại khi lỡ 6 ngày chạy (`goto 6`) | Đúng hết | Mất lịch sử trạng thái đơn, giá sản phẩm, số điện thoại | `check.py` |
| Trả lời "W0013 từng ở trạng thái nào, kho biết lúc nào" | Chỉ trạng thái hiện tại | Đủ lịch sử, có thời điểm | 1 query |
| Thêm sàn TMĐT (khách mã riêng) | Sửa `dim_customer`, `int_sales__lines`, logic hợp nhất | Thêm stage + satellite + same-as link, mart thêm 1 nhánh | thí nghiệm tư duy |

Rồi **gắn với bối cảnh adventure_works**: mấy nguồn? (1 database OLTP với nhiều schema), team mấy người? (1), có yêu cầu kiểm toán? (không), dữ liệu đổi không? (tĩnh). Với bối cảnh đó, câu trả lời trung thực thường là: *"Kimball cho tầng hiển thị; Data Vault cho một phạm vi nhỏ (khách hàng, sản phẩm) để chứng minh năng lực và chuẩn bị cho kịch bản có thêm nguồn"* — kèm điều kiện xem lại.

## Gợi ý danh sách ADR cho cả roadmap

| # | Quyết định | Tuần |
|---|---|---|
| 0001 | Data Vault hay Kimball cho tầng tích hợp | 6 |
| 0002 | Chiến lược môi trường dev/staging/prod và CD (1 hay nhiều GCP project) | 5 |
| 0003 | Partition/cluster mặc định cho fact trên BigQuery | 7 |
| 0004 | Airflow + Cosmos hay Dagster | 10 |
| 0005 | Một repo hay dbt Mesh nhiều project | 12 |

## Lỗi hay gặp khi viết ADR

- Viết sau khi đã làm xong, chỉ để "hợp thức hoá" → không có phương án bị loại.
- Không có bối cảnh → người đọc không hiểu vì sao quyết định hợp lý **lúc đó**.
- So sánh toàn tính từ cảm tính, không có số.
- Một ADR chứa 5 quyết định.
- Sửa ADR cũ thay vì viết ADR mới.

## Câu hỏi tự kiểm tra

1. ADR gồm những phần nào? Vì sao phải ghi cả phương án bị loại?
2. Khi quyết định thay đổi, xử lý ADR cũ thế nào?
3. Kể 5 tiêu chí so sánh Data Vault và Kimball.
4. Kiến trúc "lai" là gì? Khi nào hợp lý?
5. Với adventure_works, bạn chọn gì? Bảo vệ câu trả lời trong 2 phút, có số liệu.

## Tài liệu

- Michael Nygard — *Documenting Architecture Decisions*: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- ADR GitHub organization (mẫu, công cụ, MADR): https://adr.github.io/
- *Building a Scalable Data Warehouse with Data Vault 2.0* — chương 1–2 (so sánh với các cách tiếp cận khác)
- *The Data Warehouse Toolkit* — chương 1 (Kimball architecture vs các kiến trúc khác)
