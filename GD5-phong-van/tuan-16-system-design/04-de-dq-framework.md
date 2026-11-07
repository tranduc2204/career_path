# 16.4 Đề 2: Thiết kế data quality framework cho cả công ty

> Nền lý thuyết: [GĐ3 tuần 9](../../GD3-ly-thuyet/README.md). Bằng chứng thực hành để kể: lab GĐ3, 6 sự cố bắt đúng ngày, 0 báo động giả.

## Đề

> *"Công ty có khoảng 500 model dbt, 4 đội dữ liệu, 30 nguồn. Mỗi tuần người dùng báo sai số ít nhất 2 lần trước khi đội dữ liệu biết. Mỗi sáng có hàng chục cảnh báo nhưng không ai đọc. Thiết kế giúp chúng tôi một data quality framework."*

Điểm khác với đề 1: đây là đề **quy trình + tổ chức** nhiều hơn kiến trúc. Người phỏng vấn muốn thấy bạn **ưu tiên**, không phải liệt kê 50 loại test.

## Bước 1: Làm rõ

| Câu hỏi | Giả định | Vì sao |
|---|---|---|
| Hai sự cố/tuần đó thuộc loại gì? | Trễ dữ liệu (40%), thiếu dữ liệu từ connector (30%), logic sai sau deploy (20%), nguồn sửa ngầm (10%) | Mỗi loại cần cơ chế khác nhau |
| Hiện có những test gì? | ~1.200 test, chủ yếu `unique`/`not_null`, tất cả severity error; ~60% model không có owner | Vấn đề chính là **nhiễu + không có chủ** |
| Cảnh báo đi đâu? | Một kênh Slack chung | → định tuyến theo chủ |
| Dữ liệu nào quan trọng nhất? | Doanh thu (BGĐ, nhà đầu tư), dữ liệu gửi đối tác, tính hoa hồng | → phân tầng mức độ quan trọng |
| Công cụ? | dbt Core trên BigQuery, Airflow, chưa có observability tool | → chọn giữa tự làm / Elementary / SaaS |
| Ngân sách và người? | 1 người làm chính 1 quý, các đội phải tham gia | → lộ trình theo giai đoạn |

**Mục tiêu đo được** (chốt với PV):

1. **Người dùng phát hiện trước** đội dữ liệu: 2/tuần → < 1/tháng trong 2 quý.
2. Cảnh báo có người xử lý (acknowledged) trong SLA: > 90%.
3. Tỷ lệ báo động giả < 10% số cảnh báo.
4. 100% tài sản Tier 1 có owner, contract, SLA freshness, test khoá, đối soát.

## Bước 2: Ước lượng

500 model, 30 nguồn, 1.200 test. Chạy mỗi ngày ~20 phút. Nếu mỗi sáng 30 cảnh báo, mà 80% là test `error` lặp lại trên dữ liệu cũ hoặc test không ai sở hữu, thì thứ cần thêm **không phải** test, mà là bỏ bớt, phân loại và định tuyến.

## Bước 3: Kiến trúc framework

```
                         ┌───────── TIER (mức quan trọng của tài sản) ─────────┐
                         │ T1: dữ liệu ra ngoài / BGĐ / tiền   T2: vận hành nội bộ   T3: thử nghiệm │
                         └──────────────────────────────┬──────────────────────┘
                                                        │ quyết định mức kiểm tra + SLA + ai trực
 NGĂN (trước khi sai lan ra)        PHÁT HIỆN (khi đang chạy)              PHẢN ỨNG (sau khi phát hiện)
 ─ data contract với đội nguồn      ─ source freshness (sync log)          ─ severity theo tier
 ─ model contract trên public mart  ─ volume / null / distribution anomaly ─ định tuyến cảnh báo đến OWNER
 ─ CI: slim CI + unit test +        ─ test luật ở staging                  ─ runbook theo loại tín hiệu
   data diff trên model T1          ─ đối soát với nguồn / tài chính       ─ incident: SEV, thông báo người dùng
 ─ review checklist                 ─ test nghiệp vụ ở mart                ─ postmortem → thêm cơ chế ngăn
                                    ─ freshness của mart theo SLA
                                                        │
                         ĐO LƯỜNG: TTD, TTR, % do người dùng phát hiện, báo động giả, độ phủ theo tier
                         (đọc từ run_results / Elementary / bảng incident → dashboard "sức khoẻ dữ liệu")
```

## Bước 4: Đi sâu

### 4.1 Phân tầng tài sản (tiering): xương sống của framework

| | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Ví dụ | Doanh thu, dữ liệu gửi đối tác / cơ quan quản lý, hoa hồng | Dashboard vận hành, marketing | Phân tích ad-hoc, thử nghiệm |
| Owner + on-call | Bắt buộc, có trực | Bắt buộc | Khuyến khích |
| Contract (model) | Bắt buộc | Public thì bắt buộc | Không |
| Freshness SLA | Có, cảnh báo đi on-call | Có, cảnh báo kênh của đội | Không |
| Test tối thiểu | khoá, relationships, luật nghiệp vụ, anomaly volume, **đối soát** | khoá, luật chính | khoá |
| Severity khi lỗi | error ở staging (chặn), cảnh báo trang (page) | warn + ticket | warn |
| Thay đổi | CI có data diff, 2 người duyệt | 1 người duyệt | tự do |

Cách gán: `meta: {tier: 1, owner: ...}` trên model (hoặc trên exposure, rồi lan ngược lên các model upstream của exposure Tier 1 bằng script đọc manifest). CI chặn PR thêm model Tier 1 thiếu các mục bắt buộc.

### 4.2 Giảm nhiễu trước, thêm test sau (30 ngày đầu)

1. Xuất `run_results` 30 ngày → xếp hạng test theo số lần fail.
2. Test fail **liên tục** trên dữ liệu đã biết sai: sửa dữ liệu, hoặc đặt `where` (chỉ kiểm dữ liệu mới), hoặc `warn` + ticket. Đừng để nó đỏ mãi.
3. Test không có owner → gán owner theo model, hoặc xoá.
4. Severity mặc định `error` cho mọi thứ → chuyển sang theo tier.
5. Kết quả mong đợi: 30 cảnh báo/sáng còn 3–5, mỗi cái có chủ.

### 4.3 Phát hiện: chọn đúng loại kiểm tra cho đúng loại sự cố

| Loại sự cố (từ bước 1) | Cơ chế | Ghi chú |
|---|---|---|
| Trễ dữ liệu (40%) | Freshness theo **sync log** (connector chạy chưa) + freshness theo dữ liệu (có dòng mới chưa) cho nguồn dày; freshness của mart Tier 1 theo SLA | Lab GĐ3 Q1: bảng ít đổi đo bằng sync log, tránh báo động giả |
| Thiếu dữ liệu (30%) | Volume anomaly theo ngày; **so số dòng với nguồn** (connector báo số dòng đã kéo) cho nguồn Tier 1 | Anomaly cần lịch sử đủ dài, kiểm tra seasonality |
| Logic sai sau deploy (20%) | Unit test cho logic khó; **data diff** trong CI cho model Tier 1 (so bản PR với prod theo khoá và theo tổng); test hồi quy "số kỳ đã khoá không đổi" | Đây là chỗ CI rẻ nhất |
| Nguồn sửa ngầm (10%) | Schema change, distribution anomaly; đối soát tổng theo kỳ với hệ thống nguồn | Đẩy về data contract với đội nguồn |

### 4.4 Phản ứng: định tuyến và quy trình

- **Định tuyến:** owner trong `meta`/group → kênh của đội; Tier 1 → on-call (PagerDuty/Opsgenie). Một cảnh báo phải trả lời được: *cái gì hỏng, ảnh hưởng dashboard nào (exposure), ai xử lý, runbook ở đâu*.
- **Thông báo người dùng:** banner trên dashboard Tier 1 ("số hôm nay chưa đầy đủ, dự kiến 09:00") thay vì để họ tự phát hiện. Đây là đòn bẩy lớn nhất cho mục tiêu 1.
- **Incident và postmortem:** SEV1–3, mỗi postmortem phải ra **ít nhất một cơ chế ngăn hoặc phát hiện mới**.

### 4.5 Công cụ: tự làm, Elementary, hay SaaS?

| | dbt test + script tự viết | **Elementary OSS** | SaaS (Monte Carlo, Metaplane, Elementary Cloud, Bigeye...) |
|---|---|---|---|
| Chi phí tiền | Thấp | Thấp | Cao (theo bảng / theo quy mô) |
| Công vận hành | Cao | Trung bình | Thấp |
| Anomaly tự động | Phải tự viết | Có (theo cấu hình) | Có, tự học, phủ rộng không cần cấu hình |
| Lineage + cảnh báo theo owner | Tự làm | Có (report, Slack) | Có, mạnh |
| Hợp khi | Rất nhỏ | **dbt-first, ngân sách vừa** (bối cảnh này) | Nhiều nguồn ngoài dbt, ngân sách lớn |

Chọn: Elementary OSS + dbt test, bảng sức khoẻ tự dựng từ artifact. Xem lại sau 2 quý: nếu công vận hành > 0,5 người thì cân nhắc SaaS.

## Bước 5: Lộ trình triển khai

| Tuần | Việc | Kết quả |
|---|---|---|
| 1–2 | Kiểm kê: owner, tier cho 50 tài sản quan trọng nhất (bắt đầu từ exposure) | Danh sách T1 |
| 3–4 | Giảm nhiễu (4.2), định tuyến cảnh báo theo owner | 30 → ≤ 5 cảnh báo/sáng |
| 5–8 | T1: freshness + volume + đối soát + contract; banner trên dashboard | Người dùng thấy cảnh báo trước khi tự phát hiện |
| 9–10 | CI: data diff cho T1, checklist PR, unit test cho 10 logic khó nhất | Giảm lỗi sau deploy |
| 11–12 | Dashboard sức khoẻ dữ liệu + họp review hằng tháng với các đội | Đo được 4 mục tiêu |
| Q2 | Data contract với 5 đội nguồn có nhiều sự cố nhất; mở rộng cho T2 | |

## Câu hỏi đào sâu + ý trả lời

1. **"Đội khác không chịu làm owner?"** → Gắn với thứ họ quan tâm: dashboard của họ có banner đỏ khi dữ liệu họ sở hữu hỏng. Ban lãnh đạo chốt chính sách "không owner thì không lên Tier 1". Bắt đầu từ đội có động lực nhất, đưa số liệu cải thiện cho đội khác xem.
2. **"Anomaly báo nhầm nhiều quá?"** → Kiểm tra training period/seasonality, chỉnh sensitivity, `anomaly_direction` (chỉ bắt drop cho volume), loại ngày lễ, hoặc thay bằng so sánh với nguồn. Theo dõi tỷ lệ báo nhầm của từng monitor; monitor nào báo nhầm 2 lần mà không đáng thì bỏ.
3. **"Chặn pipeline hay không?"** → Chặn khi số sai sẽ **ra ngoài** hoặc làm sai quyết định tiền bạc (Tier 1, test luật chắc chắn). Không chặn cho anomaly hay test thống kê. Ngoại lệ: test ở **source** chặn cả nhánh → đặt ở staging, cân nhắc kỹ (lab GĐ3 Q3).
4. **"Data diff là gì, tốn không?"** → So bảng của PR với prod: số dòng, khoá thêm/mất, cột thay đổi giá trị. Chỉ chạy cho model T1 bị đụng (state:modified), trên mẫu hoặc partition gần nhất để giới hạn chi phí. Công cụ: tự viết SQL (EXCEPT theo khoá + so tổng), package `audit_helper` của dbt Labs, hoặc dịch vụ thương mại (Datafold, tính năng diff của dbt platform).
5. **"Đo chất lượng dữ liệu thế nào cho ban giám đốc hiểu?"** → 3 con số: % ngày tài sản T1 đúng SLA, số sự cố người dùng phát hiện trước, thời gian khắc phục trung bình. Không đưa "số test pass".

## Mid và Senior

- **Mid:** biết các loại test, Elementary, severity, freshness, có runbook. Đưa ra được tiering và lộ trình.
- **Senior:** bắt đầu từ **dữ liệu sự cố** (phân loại 2 sự cố/tuần), đặt mục tiêu đo được, nói tới tổ chức (owner, on-call, chính sách), giảm nhiễu trước khi thêm test, có tiêu chí xem lại quyết định công cụ.

## Lỗi hay gặp

- Mở đầu bằng "em sẽ thêm Great Expectations / Monte Carlo". Công cụ không sửa được vấn đề không có owner.
- Đề xuất thêm hàng trăm test trong khi vấn đề là nhiễu.
- Không có cách đo thành công.
- Bỏ qua việc **thông báo người dùng**.
