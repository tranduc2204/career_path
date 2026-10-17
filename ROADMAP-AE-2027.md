# Lộ trình Analytics Engineer: Mid gần Senior (15/10/2026 → 28/02/2027)

> Dựa trên [ROADMAP-AE](https://github.com/tunguyenn99/data-road-map-by-roles/blob/main/roadmap_viet/ROADMAP-AE.md) và hồ sơ hiện tại ([tranduc.site](https://tranduc.site/landing/), [GitHub](https://github.com/tranduc2204)).
> Thời lượng: 20 tuần, 12 tiếng/ngày, 6 ngày/tuần, khoảng 70 giờ/tuần. Chủ nhật học nửa ngày để ôn và nghỉ.

---

## 1. Kết luận

| | Đến 28/02/2027 |
|---|---|
| **Kỹ năng đạt Mid** | ✅ Đạt được. 20 tuần × 70h ≈ 1.400 giờ. Gói full-time 10 tuần × 8h của roadmap (≈ 400 giờ) mới chỉ đưa người học lên Junior, nên với số giờ này bạn đủ để làm hết Phase 2 và Phase 3. |
| **Kiến thức chạm tới Senior** | ⚠️ Được một phần: Data Mesh, tự viết dbt package, thiết kế platform, AI context layer. |
| **Title Mid khi đi xin việc** | ⚠️ Ở ranh giới. Roadmap tính Mid là 2–4 năm kinh nghiệm. Bạn có khoảng 1,5–2 năm nếu tính cả BRAVO (stored procedure, BI reporting, data migration) và Estuary. Cần trình bày 2 kinh nghiệm này thành kinh nghiệm data thật. |
| **Title Senior** | ❌ Không thể đạt trong 4,5 tháng. Senior được đánh giá bằng 4 năm production trở lên, kinh nghiệm dẫn dắt team và các quyết định kiến trúc thật. Không có khóa tự học nào thay được những thứ đó. |

Kết quả thực tế nên nhắm: **ứng tuyển Mid** (lương roadmap 28–55 triệu), hoặc **Junior+ với mức lương cao**. Bên cạnh đó, có portfolio ở mức Senior để nổi bật hơn các ứng viên cùng số năm kinh nghiệm.

---

## 2. Skill gap so với Mid/Senior

| Skill | Yêu cầu Mid → Senior | Cần thêm vào lộ trình |
|---|---|---|
| dbt | Framework design, custom materializations | Tự viết dbt package, custom materialization, custom generic test |
| Data Modeling | Data Vault, enterprise modeling | **Data Vault 2.0**, accumulating snapshot fact |
| Git & CI/CD | Pipeline design, GitOps | Tách 3 môi trường dev/staging/prod, CD tự deploy khi merge |
| Cloud DW | Cost optimization, architecture | Performance playbook cho cả Snowflake và BigQuery |
| Data Quality | Quality framework, observability platform | SLA, anomaly detection, incident runbook, data contracts |
| Semantic Layer | Design MetricFlow/Cube, enterprise metrics | MetricFlow kèm thử Cube.js, có bài so sánh |
| Orchestration | Configure, design patterns | Airflow + Cosmos **và** Dagster dùng dbt assets |
| Governance | Ownership, classification, framework | Data catalog (OpenMetadata), PII masking, policy tags |
| Python | Testing frameworks, platform tools | pytest, công cụ CLI đọc `manifest.json` |
| Soft skill | Standards, ADRs, lead initiatives | Viết ADR, SQL style guide, architecture blueprint |
| Portfolio | Mid: multi-team dbt project. Senior: mono → multi-repo, AI context layer | Dự án **dbt Mesh** và **AI context layer** |

**Không học trong giai đoạn này:** đào sâu Spark, Kafka, Delta Lake, streaming (bạn đã có đủ ở mức cần cho AE).

---

## 3. Lịch 1 ngày (12 tiếng)

| Giờ | Việc | Thời lượng |
|---|---|---|
| 07:30–11:30 | Học lý thuyết: khóa học, docs, sách | 4h |
| 13:00–17:00 | Build project: code, commit | 4h |
| 18:30–20:30 | Tuần 1–7: luyện SQL (repo `xomdata-practice`). Từ tuần 8: luyện phỏng vấn Mid/Senior | 2h |
| 20:30–22:30 | Viết README/docs/blog, đọc tài liệu tiếng Anh, tổng kết ngày | 2h |

---

## 4. Lộ trình chi tiết

### GĐ1 (T1–3, 15/10 → 4/11): Xong Phase 2, rút gọn còn 3 tuần

| Tuần | Output trên `adventure_works` |
|---|---|
| **1** (15–21/10) | Tách tầng staging/intermediate/marts. Cài dbt-utils, codegen, dbt-expectations. Viết thư viện 5 macro |
| **2** (22–28/10) | 3 chiến lược incremental (append, merge, delete+insert), late-arriving data, backfill, snapshot timestamp/check, custom generic test |
| **3** (29/10–4/11) | GitHub Actions chạy sqlfluff và slim CI (`state:modified+`). Docs lên GitHub Pages. Thêm contracts, exposures, freshness, pre-commit dùng dbt-checkpoint |

✅ **Mốc 4/11: xong mức Junior.** Sửa luôn CV và portfolio: lỗi lệch ngày ở Estuary, đưa adventure_works lên đầu.

### GĐ2 (T4–7, 5/11 → 2/12): Modeling và Warehouse mức Mid

| Tuần | Output |
|---|---|
| **4** (5–11/11) | Kimball chuyên sâu: bus matrix, grain, bridge table, factless fact, accumulating snapshot, late-arriving facts |
| **5** (12–18/11) | **Project 2 trên BigQuery** (`thelook_ecommerce`). Có 3 môi trường dev/staging/prod và CD: merge vào main thì tự deploy prod |
| **6** (19–25/11) | **Data Vault 2.0** dùng `automate_dv`, xây raw vault → business vault → marts trên adventure_works. Viết ADR so sánh Data Vault với Kimball |
| **7** (26/11–2/12) | **Performance playbook**: Snowflake (query profile, clustering, sizing, resource monitor) và BigQuery (partition, cluster, đo cost qua `INFORMATION_SCHEMA.JOBS`) |

### GĐ3 (T8–11, 3/12 → 30/12): Các thành phần platform mức Mid

| Tuần | Output |
|---|---|
| **8** (3–9/12) | **Semantic layer**: MetricFlow với 15 metric (gồm cả ratio, derived, cumulative). Dựng thử Cube.js và viết bài so sánh |
| **9** (10–16/12) | **DQ framework**: Elementary, SLA freshness cho từng mart, anomaly detection, incident runbook, data contracts. 👉 **Bắt đầu nộp CV vị trí Mid, 5–10 chỗ mỗi tuần** |
| **10** (17–23/12) | Airflow + Cosmos và Dagster dbt assets, viết ADR chọn công cụ. Governance: groups, access, versions, PII masking, policy tags, OpenMetadata lấy lineage từ dbt |
| **11** (24–30/12) | ✅ **Thi dbt Analytics Engineering Certification**. Viết pytest cho pipeline dlt |

### GĐ4 (T12–15, 31/12 → 27/1): Capstone hướng Senior và nộp CV mạnh trước Tết

| Tuần | Output |
|---|---|
| **12** (31/12–6/1) | **dbt Mesh**: tách adventure_works thành 3 project (platform, sales, finance), dùng `dbt-loom` để ref chéo project, có public models và versioning |
| **13** (7–13/1) | **Platform tooling**: tự viết dbt package đăng lên GitHub, custom materialization, CLI Python đọc `manifest.json` để báo cáo ownership và test coverage ngay trong CI |
| **14** (14–20/1) | **AI context layer**: semantic layer kết hợp dbt MCP server. Đánh giá 50 câu hỏi, so sánh kết quả có và không có semantic layer, rồi viết blog |
| **15** (21–27/1) | **Architecture blueprint** cho toàn platform, bộ ADR, SQL style guide. Viết lại CV theo hướng Mid AE. Nộp 20 chỗ trở lên |

### GĐ5 (T16–20, 28/1 → 28/2): Tết và phỏng vấn

| Tuần | Việc |
|---|---|
| **16** (28/1–3/2) | Luyện system design: transformation layer cho ngân hàng, DQ framework, CI/CD nhiều môi trường. Thêm các câu hỏi Senior: mono hay multi-repo, metric tập trung hay theo domain, context engineering |
| **17** (4–10/2) | Tết (6/2/2027), chỉ ôn nhẹ |
| **18–20** (11–28/2) | Nộp CV đợt sau Tết (10–15 chỗ mỗi tuần), làm take-home, phỏng vấn, học bù chỗ hổng ngay trong ngày |

---

## 5. Kết quả sau 28/02/2027

- **3 project:** `adventure_works` (Kimball + Data Vault + Mesh) và project BigQuery (multi-env + semantic layer + DQ), kèm thêm dbt package tự viết và AI context layer.
- **Chứng chỉ:** dbt Analytics Engineering Certification.
- **Tài liệu:** khoảng 5 ADR, performance playbook, architecture blueprint, 3–4 bài blog.

Bộ này khớp với phần portfolio Mid của roadmap, cộng thêm 2/3 project mẫu mà roadmap đặt cho Senior: mono → multi-repo và AI context layer.

## 6. Khi bị trễ tiến độ

- **Cắt theo thứ tự:** Cube.js → Dagster → custom materialization.
- **Giữ đến cùng:** CI/CD, Data Vault, semantic layer, DQ framework, dbt Mesh, chứng chỉ dbt.

## 7. Tài liệu chính (từ roadmap)

- dbt Learn (miễn phí): *dbt Fundamentals*, *Advanced Materializations*, *Jinja, Macros & Packages*
- Sách: *Analytics Engineering with SQL and dbt* (Machado & Russa), *The Data Warehouse Toolkit* (Kimball), *Building a Scalable Data Warehouse with Data Vault 2.0* (Linstedt)
- dbt Best Practices guide, dbt Developer Blog, Locally Optimistic, The Analytics Engineering Roundup
- Cộng đồng: dbt Community Slack, DataTalks.Club
