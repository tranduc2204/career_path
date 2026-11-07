# 18.2 CV và portfolio cho Mid Analytics Engineer

> Roadmap đã nêu 2 việc: trình bày **BRAVO** (stored procedure, BI reporting, data migration) và **Estuary** thành kinh nghiệm dữ liệu thật, và sửa **lỗi lệch ngày ở Estuary** trên CV. Đưa `adventure_works` lên đầu portfolio.
> Các dòng mẫu dưới đây có chỗ `[…]` để **điền số thật của bạn**. Đừng điền số không có thật: vòng phỏng vấn sẽ hỏi.

## Cấu trúc CV (1–2 trang)

1. **Tiêu đề + 2–3 dòng tóm tắt** viết theo vị trí: *"Analytics Engineer với ~[1,5–2] năm làm dữ liệu (SQL Server, CDC, BI), xây dbt project trên Snowflake/BigQuery với CI/CD 3 môi trường, Data Vault, semantic layer và DQ framework. Chứng chỉ dbt Analytics Engineering."*
2. **Kỹ năng** nhóm theo việc, không liệt kê dài: *Modeling* (Kimball, Data Vault 2.0, SCD2, semantic layer) · *dbt* (incremental/microbatch, macros, packages, contracts, versions, Mesh) · *Warehouse* (Snowflake, BigQuery, DuckDB; performance & cost) · *DQ/Ops* (Elementary, freshness SLA, CI/CD GitHub Actions, Dagster/Airflow) · *Ngôn ngữ* (SQL, Python, pytest).
3. **Kinh nghiệm** (mới nhất trước), mỗi việc 3–5 dòng theo công thức bên dưới.
4. **Project** (2–3 cái, có link GitHub + README chất lượng).
5. **Chứng chỉ, học vấn.**

## Công thức một dòng kinh nghiệm

**Động từ + việc + công cụ + kết quả có số + phạm vi.**

| Yếu | Mạnh |
|---|---|
| "Viết stored procedure cho báo cáo" | "Tối ưu [N] stored procedure báo cáo kế toán trên SQL Server, giảm thời gian chạy đêm từ [A] xuống [B] phút cho [K] khách hàng ERP" |
| "Làm data migration" | "Chuyển dữ liệu [loại] của [N] khách hàng khi nâng cấp phiên bản ERP, viết script đối soát số dư trước/sau, [0] sai lệch khi nghiệm thu" |
| "Làm việc với Estuary" | "Cấu hình/vận hành [N] pipeline CDC [nguồn → đích] bằng Estuary Flow, xử lý [schema drift / trùng dữ liệu]…" |
| "Biết dbt" | "Xây dbt project [N] model trên Snowflake (Kimball + Data Vault), CI slim + CD tự động, contract cho [N] mart public" |

## Project nên đưa (thứ tự)

| Project | Câu một dòng cho CV | Link phải có |
|---|---|---|
| `adventure_works` (Snowflake) | "Kho dữ liệu bán hàng end-to-end: staging → Data Vault → Kimball → dbt Mesh 3 project; CI/CD, contract, versions, performance playbook" | README có sơ đồ, bus matrix, ADR, ảnh lineage |
| `thelook-analytics` (BigQuery) | "3 môi trường dev/CI/prod, CD khi merge, WIF không key; semantic layer 10+ metric; Elementary DQ" | Ảnh CI xanh, workflow |
| Take-home Sen Bank (sau khi làm) | "CDC → số dư ngày dày đặc → đối soát sổ cái; phát hiện lệch GL; incremental có lookback" | README giả định / quyết định |
| Blog (2–4 bài) | MetricFlow vs Cube; DQ framework bắt 6 sự cố; AI context layer | tranduc.site |
| Package dbt tự viết / CLI đọc manifest (GĐ4) | "Package [tên] trên GitHub, CLI báo cáo ownership/test coverage trong CI" | |

## README project: người tuyển dụng đọc 60 giây

```
# Tên project — 1 câu: giải quyết vấn đề gì
[Sơ đồ kiến trúc 1 hình]
## Điểm chính (3–5 gạch đầu dòng có số)
## Mô hình dữ liệu (bus matrix / ERD, grain các fact)
## Chất lượng & vận hành (test, CI/CD, SLA)
## Quyết định & đánh đổi (link ADR)
## Chạy thử (3 lệnh)
```

## Kiểm tra trước khi gửi

- [ ] Ngày tháng mọi kinh nghiệm **khớp nhau** (CV, LinkedIn, portfolio). Đây là lỗi roadmap đã chỉ ra ở mục Estuary
- [ ] Mỗi dòng kinh nghiệm có ít nhất một con số hoặc phạm vi
- [ ] Không ghi công nghệ mà bạn không trả lời nổi 3 câu hỏi về nó
- [ ] Link GitHub mở được, README không lỗi, project chạy được theo hướng dẫn
- [ ] Tên file `TranDuc_AnalyticsEngineer_CV.pdf`; bản tiếng Anh nếu nộp công ty nước ngoài
- [ ] 3 dòng đầu chỉnh theo JD của từng công ty

## Kể về số năm kinh nghiệm (roadmap: ranh giới Mid)

Câu hỏi "bạn có bao nhiêu năm kinh nghiệm?" → đừng chỉ nói con số. *"Em có khoảng [X] năm làm việc trực tiếp với dữ liệu: [BRAVO: SQL Server, báo cáo, chuyển dữ liệu], [Estuary: CDC]. 5 tháng gần đây em tập trung vào analytics engineering hiện đại, và em có thể cho anh/chị xem [project] với những thứ một AE Mid làm hằng ngày: CI/CD nhiều môi trường, DQ framework, semantic layer."* Sau đó **chuyển ngay sang bằng chứng**.
