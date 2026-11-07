# GĐ5 — Phỏng vấn (28/1 → 28/2/2027): System design, Tết, ứng tuyển

> Roadmap: tuần 16 luyện **system design** (transformation layer ngân hàng, DQ framework, CI/CD nhiều môi trường + câu Senior: mono/multi-repo, metric tập trung/domain, context engineering); tuần 17 Tết ôn nhẹ; tuần 18–20 nộp 10–15 CV/tuần, take-home, phỏng vấn, học bù trong ngày.
> Kết quả nhắm tới: **offer Mid AE** (roadmap: 28–55 triệu), hoặc Junior+ lương cao, kèm portfolio ở mức Senior.

## Bản đồ

```
TUẦN 16: SYSTEM DESIGN (trọng tâm)
  16.0 khung 6 bước + cách chấm ──▶ 16.1 ước lượng nhanh ──▶ 16.2 thư viện mẫu thiết kế (từ vựng)
                │
                ▼  8 đề giải mẫu đầy đủ                                       luyện
  ┌─ Mid ───────────────────────────────────────┐ ┌─ Senior ─────────────────┐  16.11 14 đề + 8 câu Senior
  │ 1 ngân hàng (transformation layer) ★        │ │ 5 metric tập trung/domain │  16.12 phiếu tự chấm /42
  │ 2 DQ framework   3 CI/CD nhiều môi trường    │ │ 6 mono/multi-repo, Mesh   │  tools/drill.py (rút đề + đồng hồ)
  │ 4 stored procedure → dbt (BRAVO)            │ │ 7 context engineering AI  │
  │ 8 dashboard gần real-time (Estuary)         │ └──────────────────────────┘
  └─────────────────────────────────────────────┘
                │ biến khung thành code
                ▼
  ../bai-tap-take-home: "Ngân hàng số Sen" (CDC → số dư ngày → đối soát GL), tự chấm

TUẦN 17: TẾT, ôn nhẹ: 60 flashcard
TUẦN 18–20: phễu ứng tuyển · CV/portfolio · STAR · live SQL/dbt · take-home · offer · nhật ký + học bù
```

## Mục lục

### Tuần 16 (28/1 → 3/2): System design
| # | File | Nội dung |
|---|---|---|
| 16.0 | [00-khung-tra-loi.md](tuan-16-system-design/00-khung-tra-loi.md) | AE system design khác SWE/DE thế nào, khung 6 bước, rubric Junior/Mid/Senior, lỗi hay gặp, câu chuyển cảnh |
| 16.1 | [01-uoc-luong-nhanh.md](tuan-16-system-design/01-uoc-luong-nhanh.md) | Con số nên thuộc, chi phí Snowflake/BigQuery, quy tắc ra quyết định, 3 bài ước lượng có đáp số |
| 16.2 | [02-thu-vien-mau-thiet-ke.md](tuan-16-system-design/02-thu-vien-mau-thiet-ke.md) | 10 nhóm mẫu: ingest, phân tầng, mô hình, thời gian/dữ liệu trễ, idempotency, DQ, môi trường, bảo mật, chi phí, tổ chức |
| 16.3 | [03-de-ngan-hang-transformation-layer.md](tuan-16-system-design/03-de-ngan-hang-transformation-layer.md) | ★ **Đề 1** giải mẫu đầy đủ: hội thoại làm rõ, ước lượng, kiến trúc 5 tầng, CDC, số dư ngày, as-reported, đối soát GL, phân loại nợ, vận hành, lộ trình, 10 câu đào sâu, kịch bản 45 phút |
| 16.4 | [04-de-dq-framework.md](tuan-16-system-design/04-de-dq-framework.md) | **Đề 2**: tiering tài sản, giảm nhiễu trước, phát hiện theo loại sự cố, định tuyến cảnh báo, chọn công cụ, lộ trình 12 tuần |
| 16.5 | [05-de-cicd-nhieu-moi-truong.md](tuan-16-system-design/05-de-cicd-nhieu-moi-truong.md) | **Đề 3**: quyền theo môi trường, slim CI + contract + data diff, CD và blue-green/rollback, UAT cho model tiền, dbt platform khác gì |
| 16.6 | [06-de-chuyen-stored-procedure-sang-dbt.md](tuan-16-system-design/06-de-chuyen-stored-procedure-sang-dbt.md) | **Đề 4**: kiểm kê, golden output, dịch procedure thành DAG, khi procedure cũ sai, thứ tự cắt chuyển, kể bằng kinh nghiệm BRAVO |
| 16.7 | [07-de-metric-tap-trung-hay-domain.md](tuan-16-system-design/07-de-metric-tap-trung-hay-domain.md) | **Đề 5** (Senior): mô hình liên bang, metric certified, chống trùng, câu trả lời 2 phút |
| 16.8 | [08-de-mono-hay-multi-repo.md](tuan-16-system-design/08-de-mono-hay-multi-repo.md) | **Đề 6** (Senior): project vs repo, triệu chứng nào cần tách, thiết kế Mesh trong mono-repo, kế hoạch chuyển |
| 16.9 | [09-de-context-engineering-ai.md](tuan-16-system-design/09-de-context-engineering-ai.md) | **Đề 7** (Senior): vì sao text-to-SQL sai, semantic layer làm API số liệu, metadata, MCP, bộ đánh giá |
| 16.10 | [10-de-dashboard-gan-thoi-gian-thuc.md](tuan-16-system-design/10-de-dashboard-gan-thoi-gian-thuc.md) | **Đề 8**: hỏi đúng độ trễ, 4 phương án, lambda nhẹ, kể bằng kinh nghiệm Estuary |
| 16.11 | [11-ngan-hang-de-luyen-them.md](tuan-16-system-design/11-ngan-hang-de-luyen-them.md) | 14 đề D1–D14 (câu phải hỏi, quyết định, bẫy) + 8 câu Senior ngắn |
| 16.12 | [12-phieu-tu-cham.md](tuan-16-system-design/12-phieu-tu-cham.md) | Quy trình buổi luyện 75 phút, phiếu chấm 14 tiêu chí /42, câu đào sâu đa năng, nhật ký luyện |
| — | [tools/drill.py](tools/drill.py) | `python tools/drill.py` rút đề ngẫu nhiên, chạy đồng hồ 6 bước |

### Tuần 17 (4/2 → 10/2): Tết
- [tuan-17-tet/on-nhe-va-flashcard.md](tuan-17-tet/on-nhe-va-flashcard.md): lịch ≤ 1–2 giờ/ngày + 60 flashcard (dbt, mô hình, nền tảng, ngân hàng).

### Tuần 18–20 (11/2 → 28/2): Ứng tuyển và phỏng vấn
| # | File | Nội dung |
|---|---|---|
| 18.1 | [01-quy-trinh-ung-tuyen.md](tuan-18-20-phong-van/01-quy-trinh-ung-tuyen.md) | Phễu và chỗ rơi, kênh, phân loại công ty, `tracker.csv`, nhịp tuần, tin nhắn mẫu |
| 18.2 | [02-cv-va-portfolio.md](tuan-18-20-phong-van/02-cv-va-portfolio.md) | Cấu trúc CV, công thức dòng kinh nghiệm (BRAVO, Estuary), project nên đưa, README 60 giây, checklist |
| 18.3 | [03-behavioral-star.md](tuan-18-20-phong-van/03-behavioral-star.md) | STAR, 8 câu chuyện cần có, mẫu điền, 13 câu hỏi hành vi, câu hỏi nên hỏi lại |
| 18.4 | [04-vong-ky-thuat-sql-dbt.md](tuan-18-20-phong-van/04-vong-ky-thuat-sql-dbt.md) | Quy trình live SQL 5 bước, 15 dạng bài, trả lời dbt kiểu Mid, bài đọc code có đáp án |
| 18.5 | [05-take-home.md](tuan-18-20-phong-van/05-take-home.md) | Phân bổ thời gian, khung README bài nộp, vòng đọc lại bài |
| 18.6 | [06-dam-phan-offer.md](tuan-18-20-phong-van/06-dam-phan-offer.md) | Hỏi/đưa khoảng lương, gross/net, bảng so sánh offer, đàm phán, từ chối lịch sự |
| 18.7 | [07-nhat-ky-va-hoc-bu.md](tuan-18-20-phong-van/07-nhat-ky-va-hoc-bu.md) | Mẫu ghi sau phỏng vấn, quy tắc học bù trong ngày, bảng chỗ hổng |
| — | [cau-hoi-tong-hop.md](cau-hoi-tong-hop.md) | Mục lục câu hỏi GĐ1–GĐ5 + 30 câu hay gặp nhất |

### Thực hành
| Bài | Nội dung |
|---|---|
| [../bai-tap-take-home/](../bai-tap-take-home/README.md) | Take-home "Ngân hàng số Sen": email đề như thật, 6 giờ, dữ liệu CDC có r/c/u/d + phát lại + ghi sổ lùi + tỷ giá thiếu ngày + 1 lỗi sổ cái. Tự chấm 5 phần khách quan + rubric 6 tiêu chí + câu hỏi vòng đọc lại bài |
| `tools/drill.py` | Luyện system design có đồng hồ |

## Lịch theo ngày

Khung ngày giữ như roadmap. Từ tuần 16, khối 18:30–20:30 là **luyện phỏng vấn nói thành tiếng**.

**Tuần 16 — System design**

| Ngày | Sáng (07:30–11:30) | Chiều (13:00–17:00) | Tối |
|---|---|---|---|
| T5 28/1 | 16.0, 16.1, 16.2 | **Đề 1** tự làm 60 phút có ghi âm → chấm 16.12 → đọc lời giải 16.3 | Nói lại phần tổng kết + lộ trình đề 1 |
| T6 29/1 | **Đề 2** tự làm → đọc 16.4 | **Đề 3** tự làm → đọc 16.5 | Đề 1 lần 2, không nhìn |
| T7 30/1 | **Đề 4** (16.6) + viết câu chuyện BRAVO thật | **Take-home Sen Bank** (bấm giờ, 4 giờ đầu) | Take-home (2 giờ cuối) |
| CN 31/1 | `check.py` + rubric + so `dap-an/` | (nghỉ) | |
| T2 01/2 | **Đề 5, 6** (16.7, 16.8): nói câu trả lời 2 phút, ghi âm | **Đề 7, 8** (16.9, 16.10) | **Mock với người thật #1** (đề 1 hoặc 3) |
| T3 02/2 | 2 đề D (`drill.py`), 30 phút mỗi đề | Làm lại đề 2 và 3 không nhìn | STAR: 4 câu chuyện |
| T4 03/2 | **Mock #2** (đề ngẫu nhiên, người thật) | Viết **1 trang "kiến trúc chuẩn của tôi"**: sơ đồ + 10 quyết định mặc định + lý do | Nộp CV đợt cuối tháng 1 |

**Tuần 17 — Tết:** xem [tuan-17-tet](tuan-17-tet/on-nhe-va-flashcard.md).

**Tuần 18–20 — Phỏng vấn** (nhịp lặp lại mỗi tuần, chi tiết ở 18.1)

| Ngày | Sáng | Chiều | Tối |
|---|---|---|---|
| T5 | Nộp 5–8 CV (chỉnh theo JD) | Phỏng vấn / làm take-home thật | Nhật ký + học bù |
| T6 | Live SQL bấm giờ (3 bài) | Phỏng vấn / take-home | STAR 1 câu |
| T7 | 1 đề system design (`drill.py`) | Cải thiện portfolio (README, blog) | |
| CN | Xem phễu (`tracker.csv`), sửa CV | (nghỉ) | |
| T2 | Nộp 5–8 CV | Phỏng vấn / take-home | Nhật ký + học bù |
| T3 | Ôn chỗ hổng tuần (bảng 18.7) | Phỏng vấn | Flashcard |
| T4 | Mock system design với người thật (1 lần/tuần) | Phỏng vấn | Kế hoạch tuần sau |

## Checklist mốc 28/2

**System design (tuần 16)**
- [ ] Đã làm có bấm giờ 8 đề giải mẫu + ≥ 4 đề D, mỗi đề có điểm phiếu tự chấm
- [ ] Đề 1, 2, 3 làm lại lần 2 đạt ≥ 28/42
- [ ] ≥ 2 buổi mock với người thật
- [ ] 1 trang "kiến trúc chuẩn của tôi"
- [ ] Take-home Sen Bank: 5/5 khách quan, rubric trung bình ≥ 3, đưa lên GitHub

**Ứng tuyển (tuần 18–20)**
- [ ] CV bản Mid AE (tiếng Việt + tiếng Anh), ngày tháng khớp mọi nơi
- [ ] Portfolio: `adventure_works` lên đầu, README 60 giây cho 3 project
- [ ] 8 câu chuyện STAR, mỗi câu kể ≥ 3 lần
- [ ] ≥ 30 đơn nộp sau Tết (+ các đợt trước), `tracker.csv` cập nhật, phễu xem mỗi Chủ nhật
- [ ] Nhật ký sau **mọi** buổi phỏng vấn, chỗ hổng đều có ngày học bù
- [ ] 🎯 Offer Mid AE (hoặc Junior+ lương cao), quyết định bằng bảng so sánh 18.6

## Ghi chú

- **Thứ tự nên đọc mỗi đề:** đọc đề → tự làm có bấm giờ → chấm → **rồi mới** đọc lời giải. Đọc lời giải trước thì bạn sẽ nhận ra câu trả lời, nhưng không tự dựng lại được dưới áp lực.
- **Số liệu chi phí** ở 16.1 lấy theo bảng giá công khai đầu 2026, dùng để ước lượng bậc độ lớn. Khi phỏng vấn, nói rõ "theo bảng giá công khai, cần kiểm tra hợp đồng thực tế".
- **Quy định** (phân loại nợ theo Thông tư 11/2021/TT-NHNN, Luật Bảo vệ dữ liệu cá nhân 2025, Nghị định 53/2022) chỉ nêu ở mức đủ để thiết kế. Ở công ty thật, đội pháp chế / tuân thủ là người quyết định.
- **Bài take-home** đã kiểm chứng 07/11/2026: lời giải mẫu 5/5, 3 kiểu lời giải sai đều bị bắt (xem README của bài).
