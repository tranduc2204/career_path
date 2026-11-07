# 18.1 Quy trình ứng tuyển: biến việc tìm việc thành một pipeline

> Roadmap: sau Tết nộp **10–15 chỗ/tuần** (tuần 18–20), đã bắt đầu từ tuần 9 (5–10/tuần) và tuần 15 (≥ 20). Mục tiêu: **Mid AE** (lương roadmap 28–55 triệu), hoặc Junior+ lương cao.

## Phễu và con số

Nghĩ như một analytics engineer: đo phễu, tìm chỗ rơi nhiều nhất, sửa chỗ đó.

```
Nộp ──▶ Phản hồi (HR gọi) ──▶ Vòng kỹ thuật 1 ──▶ Take-home / vòng 2 ──▶ Vòng cuối ──▶ Offer
100        15–25%                  60%                   50%                  50%          
```

| Rơi nhiều ở | Nghĩa là | Sửa |
|---|---|---|
| Nộp → phản hồi | CV / kênh nộp | CV theo từng loại công ty, nộp qua giới thiệu (referral), LinkedIn nhắn người tuyển |
| Kỹ thuật 1 | SQL / dbt cơ bản | Luyện SQL bấm giờ (18.4), ôn flashcard |
| Take-home / vòng 2 | Chất lượng bài, giải thích | Làm bài take-home mẫu, README có giả định + đánh đổi |
| Vòng cuối | System design / behavioral | Mock 16.12, STAR 18.3 |

## Kênh

| Kênh | Ghi chú |
|---|---|
| Giới thiệu (referral) | Tỉ lệ phản hồi cao nhất. Nhắn người quen ở công ty mục tiêu, cộng đồng (DataTalks.Club, dbt Slack khu vực, nhóm Data Việt Nam trên Facebook/LinkedIn) |
| LinkedIn | Đăng bài về project (blog semantic layer, DQ framework) để người tuyển dụng thấy. Nhắn trực tiếp hiring manager kèm 2 dòng + link portfolio |
| ITviec, TopCV, VietnamWorks | Số lượng lớn, phản hồi thấp hơn. Lọc "Analytics Engineer", "Data Engineer (dbt)", "BI Engineer" |
| Trang tuyển dụng công ty | Ngân hàng, fintech, TMĐT lớn thường đăng ở đây trước |
| Remote / nước ngoài | Lương cao hơn, cạnh tranh hơn, phỏng vấn tiếng Anh: chuẩn bị riêng |

## Phân loại công ty để điều chỉnh CV và cách kể

| Loại | Họ quan tâm | Nhấn mạnh |
|---|---|---|
| Ngân hàng / chứng khoán / bảo hiểm | Độ đúng, đối soát, audit, bảo mật, quy trình | Take-home Sen Bank, đối soát GL, Data Vault, CI/CD có duyệt, PII |
| Fintech / ví | Tốc độ + đúng, CDC, gần real-time | Estuary (CDC), dlt + pytest, đề 10 |
| TMĐT / bán lẻ | Metric, marketing, tồn kho | Semantic layer, Kimball (Mây Shop), thelook |
| SaaS / công ty công nghệ | Modern data stack, chủ động | dbt nâng cao, package tự viết, AI context layer, Mesh |
| Công ty tư vấn / outsourcing | Đa dạng nền tảng, giao tiếp khách hàng | Snowflake + BigQuery + DuckDB, migration stored procedure (BRAVO) |

## Bảng theo dõi ứng tuyển

Tạo `tracker.csv` (hoặc Google Sheets) với các cột:

```csv
cong_ty,loai,vi_tri,kenh,ngay_nop,nguoi_lien_he,trang_thai,vong_tiep,ngay_vong_tiep,muc_luong_dang,ghi_chu,link_jd
Sen Bank,ngan_hang,Analytics Engineer,referral,2027-02-11,Chị A (DE lead),phong_van_1,take-home,2027-02-16,35-45tr,hỏi nhiều về đối soát,https://...
```

`trang_thai`: `da_nop → phan_hoi → phong_van_1 → take_home → phong_van_cuoi → offer / tu_choi / ho_rut`. Mỗi Chủ nhật: tính tỉ lệ chuyển qua từng bước (bạn làm dashboard được bằng DuckDB trong 10 phút), xem chỗ rơi.

## Nhịp một tuần (tuần 18–20)

| Buổi | Việc |
|---|---|
| Sáng T2, T5 | Nộp 5–8 chỗ, mỗi chỗ chỉnh 3 dòng đầu CV + 1 dòng tin nhắn theo JD |
| Hằng ngày 18:30–20:30 | Luyện: SQL bấm giờ (2 bài) + 1 câu STAR + 1 đề system design ngắn (luân phiên) |
| Sau mỗi phỏng vấn | Ghi nhật ký **trong ngày** (18.7), học bù ngay chỗ hổng |
| Chủ nhật | Xem phễu, sửa CV/cách kể, lên danh sách tuần sau |

## Viết tin nhắn cho người tuyển dụng (mẫu)

> *Chào anh/chị [tên], em là [tên], đang tìm vị trí Analytics Engineer. Em thấy [công ty] đang tuyển AE và đang [dùng dbt / xây kho cho mảng X]. Em vừa làm [project liên quan nhất: đối soát GL từ CDC / DQ framework bắt 6 loại sự cố] ([link]). Em gửi CV kèm theo, mong được trao đổi ạ.*

Ngắn, có một bằng chứng **liên quan tới công ty đó**, có link.
