# 16.0 System design cho Analytics Engineer: khung trả lời

## Vòng system design của AE khác của Software Engineer thế nào

| | Software Engineer | Data Engineer | **Analytics Engineer** |
|---|---|---|---|
| Câu hỏi điển hình | "Thiết kế URL shortener" | "Thiết kế pipeline ingest 1 tỷ sự kiện/ngày" | "Thiết kế tầng transformation cho ngân hàng", "Thiết kế DQ framework", "CI/CD cho dbt nhiều môi trường" |
| Trọng tâm | Latency, QPS, replication | Throughput, partition, exactly-once, streaming | **Mô hình dữ liệu, grain, độ đúng của số, ownership, vận hành, chi phí warehouse** |
| Kết quả cuối | Kiến trúc dịch vụ | Kiến trúc pipeline | **Kiến trúc tầng + mô hình (bảng nào, grain gì) + quy trình (test, deploy, sự cố)** |
| "Đúng" là gì | Hệ thống không sập | Dữ liệu không mất | **Con số đúng, giải thích được, đúng giờ, và đội khác dùng được** |

Người phỏng vấn AE ít hỏi về Kafka partition, nhiều hỏi: *"Bảng này grain gì? Nếu dữ liệu đến trễ 3 ngày thì số tháng trước có đổi không? Ai được xem cột này? Một PR sửa model này thì CI chạy gì?"*

## Khung 6 bước (45–60 phút)

```
 1. LÀM RÕ          2. ƯỚC LƯỢNG       3. KIẾN TRÚC         4. ĐI SÂU            5. VẬN HÀNH          6. TỔNG KẾT
 (5–8 phút)         (3–5 phút)         TỔNG THỂ (8–10)      (15–20 phút)         (8–10 phút)          (3–5 phút)
 người dùng?        bao nhiêu dòng?    nguồn → ingest →     2–3 chỗ khó nhất:    test, SLA, CI/CD,    đánh đổi đã chọn,
 câu hỏi nào?       bao nhiêu nguồn?   tầng → mart →        grain, SCD, late     sự cố, chi phí,      rủi ro, bước tiếp
 SLA? ràng buộc?    tăng trưởng?       người dùng           data, đối soát...    quyền truy cập       theo (v2, v3)
```

### Bước 1. Làm rõ yêu cầu (đừng bỏ qua)

Đề luôn mơ hồ **có chủ ý**. Người phỏng vấn chấm cách bạn hỏi. Hỏi theo 5 nhóm, ghi lên bảng:

| Nhóm | Câu hỏi mẫu |
|---|---|
| **Người dùng & quyết định** | Ai dùng (Finance, Risk, ban giám đốc, cơ quan quản lý)? Họ ra quyết định gì từ số này? Dashboard, báo cáo định kỳ, API, AI? |
| **Nguồn** | Bao nhiêu hệ thống? Cách lấy (CDC, file, API)? Có lịch sử không, hay chỉ trạng thái hiện tại? |
| **Độ tươi & độ đúng** | Cần số trước mấy giờ? Hằng ngày hay gần thời gian thực? Sai lệch bao nhiêu thì chấp nhận được? Số tháng đã khoá sổ có được đổi không? |
| **Ràng buộc** | Warehouse nào (hay phải chọn)? Ngân sách? Dữ liệu được ra khỏi Việt Nam không? PII? Kiểm toán? |
| **Đội & quy mô** | Bao nhiêu người làm dữ liệu, mấy đội? Bao nhiêu model hiện có? Đội đã quen công cụ nào? |

Mẹo: nếu người phỏng vấn nói *"tuỳ bạn giả định"*, hãy **nói to giả định** và viết lên bảng ("Giả định: Snowflake, 2 đội, SLA 07:00, không real-time"). Sau đó bám theo nó.

Chốt bằng **yêu cầu chức năng** (3–5 câu hỏi nghiệp vụ hệ thống phải trả lời được) và **yêu cầu phi chức năng** (SLA, độ đúng, bảo mật, chi phí, khả năng mở rộng).

### Bước 2. Ước lượng nhanh

Không cần chính xác, cần **đúng bậc độ lớn** và dùng con số để ra quyết định. Ví dụ: "Giao dịch 5 triệu/ngày × 365 × 5 năm ≈ 9 tỷ dòng ≈ 1 TB nén → full refresh mỗi ngày là bất khả, cần incremental + partition theo ngày". Bảng số tham khảo ở [16.1](01-uoc-luong-nhanh.md).

### Bước 3. Kiến trúc tổng thể

Vẽ một sơ đồ đi từ trái sang phải. **Mọi mũi tên phải có nhãn** (CDC? batch mỗi ngày? API?):

```
[nguồn] ──CDC──▶ [raw / landing] ──▶ [staging] ──▶ [integration] ──▶ [marts] ──▶ [semantic] ──▶ [người dùng]
                       │                                                              ▲
                       └──────── [DQ / observability] ── [catalog / lineage] ─────────┘
                 [orchestrator]   [CI/CD]   [quyền truy cập]   [giám sát chi phí]
```

Nói **vì sao** cho mỗi tầng (một câu). Đừng vẽ thêm hộp nào mà bạn không giải thích được.

### Bước 4. Đi sâu: chọn 2–3 chỗ khó nhất

Đây là nơi phân biệt Junior / Mid / Senior. Tự chọn chỗ khó (hoặc người phỏng vấn chọn), ví dụ:

- **Grain và khoá** của 2–3 bảng quan trọng nhất (vẽ cột).
- **Lịch sử**: SCD2 ở đâu, snapshot hay dựng từ CDC, as-of reporting.
- **Dữ liệu đến trễ / sửa ngược**: incremental + lookback, khoá sổ, restate.
- **Đối soát**: số của bạn khớp với hệ thống nguồn / GL thế nào.
- **Idempotency**: chạy lại một ngày có ra cùng kết quả không.

Với mỗi chỗ: **nêu 2 phương án → tiêu chí → chọn → hệ quả**. Đó là "tư duy đánh đổi" mà rubric chấm điểm cao.

### Bước 5. Vận hành

Hầu hết ứng viên hết giờ trước khi tới đây, nên **chủ động dành thời gian** cho nó:

- **Chất lượng**: test ở tầng nào, SLA freshness, anomaly, ai nhận cảnh báo.
- **Triển khai**: môi trường, CI (slim CI, defer), CD, rollback.
- **Sự cố**: runbook, backfill.
- **Bảo mật**: PII, phân quyền theo vai trò, masking, audit log.
- **Chi phí**: cỡ warehouse, partition/cluster, giới hạn, ai trả tiền.

### Bước 6. Tổng kết

30 giây: *"Tóm lại, em chọn X vì Y. Rủi ro lớn nhất là Z, em giảm nó bằng W. Nếu có thêm 3 tháng, em sẽ làm A, B."*

## Người phỏng vấn chấm gì

| Tiêu chí | Junior | **Mid** (mục tiêu của bạn) | Senior |
|---|---|---|---|
| Làm rõ yêu cầu | Lao vào vẽ | Hỏi đủ 5 nhóm, chốt giả định | + hỏi về quyết định kinh doanh đằng sau, tìm ràng buộc ẩn (quy định, tổ chức) |
| Mô hình dữ liệu | Liệt kê bảng | **Grain, khoá, SCD, semi-additive rõ ràng** | + biết khi nào phá chuẩn, mô hình chịu được thay đổi tổ chức |
| Đánh đổi | Một phương án | 2 phương án + lý do chọn | Đánh đổi gắn với chi phí, đội ngũ, thời gian; biết khi nào "chưa cần" |
| Vận hành | Không nhắc | Test, SLA, CI/CD, sự cố | + đo lường độ tin cậy, chi phí theo đội, lộ trình nâng cấp |
| Giao tiếp | Lan man | Có cấu trúc, vẽ rõ, kiểm tra lại với người phỏng vấn | Dẫn dắt cuộc thảo luận, điều chỉnh độ sâu theo người nghe |
| Kinh nghiệm thật | Không có | Dẫn chứng từ project (lab, adventure_works, thelook) | Câu chuyện production thật, kể cả thất bại |

## Lỗi hay gặp

1. **Không hỏi gì**, vẽ ngay kiến trúc "chuẩn" học thuộc.
2. **Liệt kê công cụ** (Kafka, Spark, Airflow, dbt, Snowflake, Looker...) mà không nói vì sao. Người phỏng vấn sẽ hỏi "nếu bỏ X thì sao?".
3. **Không nói grain.** Câu "bảng fact giao dịch" chưa phải mô hình. "1 dòng / giao dịch đã ghi sổ, khoá txn_id, trạng thái hiện tại" mới là mô hình.
4. **Quên dữ liệu đến trễ, sửa ngược, xoá.** Ở ngân hàng, đây là câu hỏi đầu tiên của người phỏng vấn.
5. **Real-time mọi thứ.** Hỏi lại xem ai cần số trong 5 phút. Thường câu trả lời là "không ai cả".
6. **Hết giờ ở bước 3**, không có vận hành.
7. **Im lặng suy nghĩ quá lâu.** Hãy nghĩ thành tiếng: "Em đang cân nhắc giữa A và B..."

## Câu "chuyển cảnh" hữu ích

- "Trước khi vẽ, cho em hỏi vài câu để chắc em hiểu bài toán..."
- "Em giả định X. Anh/chị thấy có hợp lý không, hay em nên giả định khác?"
- "Có 2 cách. Cách 1... Cách 2... Với bối cảnh này em chọn cách 2 vì..."
- "Em dừng ở mức tổng thể ở đây. Anh/chị muốn em đi sâu phần nào: mô hình dữ liệu, chất lượng hay triển khai?"
- "Nếu quy mô tăng 10 lần, chỗ đầu tiên vỡ là..."

## Luyện thế nào

- Mỗi đề trong tuần 16: **làm 1 lần có bấm giờ**, nói thành tiếng, ghi âm hoặc quay màn hình, vẽ trên giấy hoặc Excalidraw.
- Tự chấm bằng [16.12 phiếu tự chấm](12-phieu-tu-cham.md). Sau đó mới đọc lời giải mẫu.
- Làm lại đề đó sau 3 ngày, **không** nhìn lời giải.
- Ít nhất 2 buổi **mock với người thật** (bạn bè, cộng đồng DataTalks.Club, ADPList).
- Dùng `python tools/drill.py` để rút đề ngẫu nhiên và chạy đồng hồ theo 6 bước.
