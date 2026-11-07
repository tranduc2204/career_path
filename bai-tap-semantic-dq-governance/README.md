# Lab GĐ3: Semantic layer + Data Quality + Governance + Orchestration (dbt + DuckDB)

Bộ bài tập cho **tuần 8–10** của GĐ3. Chạy hoàn toàn trên máy bằng DuckDB, cùng cách vận hành với lab GĐ1–GĐ2.

Bạn vẫn làm cho **Mây Shop**, nhưng giờ là quý IV/2026: shop đã lớn, có 3 đội dữ liệu (Commerce, Customer, Growth), 60 ngày lịch sử và khoảng 110 đơn mỗi ngày. Staging và các bảng mart đã được dựng sẵn. Việc của bạn là biến chúng thành **một nền tảng dữ liệu đáng tin**:

1. **Tuần 8 (M1–M8):** semantic layer bằng MetricFlow. Gồm 15 metric đủ 4 loại (simple, ratio, derived, cumulative) và saved query. Chấm bằng `mf query` thật.
2. **Tuần 9 (Q1–Q7):** data quality framework. Có SLA freshness, Elementary anomaly detection, data contract và runbook. Script giả lập cho **7 ngày trôi qua, mỗi ngày một sự cố production**. Bộ test của bạn phải bắt đúng sự cố, đúng ngày, và **không báo động giả** vào ngày bình thường.
3. **Tuần 10 (G1–G6, O1–O5):** governance (groups, access, contracts, versions, che PII, exposures) và orchestration (Dagster + Airflow/Cosmos).

Phần so sánh Cube.js ([bai-tap/02-cube-so-sanh.md](bai-tap/02-cube-so-sanh.md)) và runbook không chấm tự động.

## Cấu trúc

```
bai-tap-semantic-dq-governance/
├── README.md
├── pyproject.toml            ← uv project: dbt-core 1.12 + dbt-duckdb + dbt-metricflow + dagster + dagster-dbt
├── bai-tap/                  ← ĐỀ BÀI
│   ├── 00-setup.md           ← cài đặt, dữ liệu, đồng hồ của lab, dòng thời gian 7 sự cố
│   ├── 01-semantic-layer.md  ← M1–M8
│   ├── 02-cube-so-sanh.md    ← dựng thử Cube trên cùng dữ liệu, viết bài so sánh (không chấm)
│   ├── 03-data-quality.md    ← Q1–Q7 + runbook
│   ├── 04-governance.md      ← G1–G6
│   ├── 05-orchestration.md   ← O1–O5 + ADR chọn orchestrator
│   └── 06-thu-thach-cuoi.md  ← tổng hợp, thử thách mở, câu hỏi phỏng vấn
├── lab/                      ← dbt project BẠN LÀM BÀI Ở ĐÂY
│   ├── models/staging/       ← 7 model staging dựng sẵn
│   ├── models/marts/         ← 8 bảng mart dựng sẵn (commerce / customer / growth)
│   ├── models/growth/        ← growth_campaign_daily: model "vi phạm" quy định truy cập (bài G2)
│   ├── macros/lab_clock.sql  ← đồng hồ giả lập (đừng sửa)
│   ├── orchestration/        ← khung Dagster (bạn viết) + project Airflow riêng
│   ├── cube/                 ← kit dựng thử Cube bằng Docker
│   └── scripts/
│       ├── simulate.py       ← cho thời gian trôi: reset / next / status / goto
│       ├── run_day.sh        ← "pipeline sáng nay": freshness + build, LƯU kết quả theo ngày
│       ├── replay.sh         ← làm lại từ ngày 0 tới ngày N rồi chấm
│       └── check.py          ← tự chấm 26 bài
└── dap-an/                   ← ĐÁP ÁN đã kiểm chứng 26/26 PASS qua replay.sh. Đừng mở trước!
```

## Bắt đầu nhanh

```bash
cd ~/Desktop/target_ae/bai-tap-semantic-dq-governance
uv sync && source .venv/bin/activate
cd lab
export DBT_PROFILES_DIR=.

dbt deps                           # dbt_utils (Elementary bạn tự thêm ở tuần 9)
python scripts/simulate.py reset   # tạo lab.duckdb, nạp ngày 0 (60 ngày lịch sử)
dbt build                          # 16 model + 30 test dựng sẵn, tất cả xanh
python scripts/check.py            # 26 bài, lúc này tất cả SKIP
```

Rồi mở [bai-tap/00-setup.md](bai-tap/00-setup.md).

## Danh sách bài

⭐ cơ bản · ⭐⭐ trung bình · ⭐⭐⭐ khá · ⭐⭐⭐⭐ nâng cao

### Tuần 8: Semantic layer (M)

| ID | Cấp | Chủ đề | Bài học chính |
|---|---|---|---|
| M1 | ⭐ | Time spine | Bảng ngày cho cumulative / offset, khai báo bằng YAML |
| M2 | ⭐⭐ | Semantic model | Entity primary/foreign, dimension, **bẫy đặt tên entity trùng từ khoá SQL** |
| M3 | ⭐⭐ | Simple metric | Filter qua entity (đơn huỷ nằm ở bảng khác), `agg_time_dimension` khác nhau |
| M4 | ⭐⭐⭐ | Ratio | Ratio của tổng ≠ trung bình của ratio, ratio giữa 2 semantic model |
| M5 | ⭐⭐⭐ | Derived | `offset_window`, NULL lan truyền, **`fill_nulls_with` bị bỏ qua ở dbt 1.12.6** |
| M6 | ⭐⭐⭐⭐ | Cumulative | `grain_to_date`, `window`, distinct trong cửa sổ, **`period_agg`** |
| M7 | ⭐⭐⭐ | Truy vấn theo dimension | Join qua entity, conformed dimension `marketing_channel` |
| M8 | ⭐⭐ | Saved query | Truy vấn đặt tên cho dashboard, `exports` |

### Tuần 9: Data quality (Q). Chấm qua `replay.sh`

| ID | Cấp | Sự cố | Bài học chính |
|---|---|---|---|
| Q1 | ⭐⭐⭐ | Connector quảng cáo chết 3 ngày | SLA warn/error, **đo freshness theo nhật ký sync** cho bảng ít đổi |
| Q2 | ⭐⭐⭐ | Chỉ về 30% đơn của một ngày | `volume_anomalies`, training/detection period, **bẫy seasonality** |
| Q3 | ⭐⭐⭐ | 90% phiên mất customer_id | Cột được phép NULL: anomaly `null_percent` chứ không phải `not_null` |
| Q4 | ⭐⭐ | Thanh toán mới `bnpl` | Thay đổi nghiệp vụ ≠ lỗi: `severity: warn` |
| Q5 | ⭐⭐⭐⭐ | CRM đổi tên cột | `schema_changes` + staging tự thích nghi bằng `adapter.get_columns_in_relation` |
| Q6 | ⭐⭐⭐ | App ghi giá theo nghìn đồng | Luật nghiệp vụ biết trước → test luật, `severity: error` để **chặn** downstream |
| Q7 | ⭐⭐ | (ngày sạch) | Không báo động giả, không model nào lỗi |

### Tuần 10: Governance (G) và Orchestration (O)

| ID | Cấp | Chủ đề | Bài học chính |
|---|---|---|---|
| G1 | ⭐ | Groups | Chủ sở hữu theo đội, gán theo folder |
| G2 | ⭐⭐ | Access | private / protected / public, sửa model của đội khác đang ref sai |
| G3 | ⭐⭐⭐ | Contracts | `data_type` cho mọi cột, **HUGEINT của DuckDB** |
| G4 | ⭐⭐⭐ | Versions | v1 → v2, `deprecation_date`, `defined_in`, **semantic model trên model có version** |
| G5 | ⭐⭐⭐ | PII | Gắn nhãn `meta.pii`, macro che dữ liệu theo target |
| G6 | ⭐ | Exposures | Dashboard phụ thuộc model public và metric |
| O1 | ⭐⭐ | Dagster: dbt → asset | `@dbt_assets`, loại package Elementary |
| O2 | ⭐⭐ | Dagster translator | Asset key cho source, group theo đội |
| O3 | ⭐ | Dagster schedule | 06:30 giờ Việt Nam |
| O4 | ⭐⭐ | Asset check + chạy | Test dbt thành asset check, materialize một phần đồ thị |
| O5 | ⭐⭐⭐ | Airflow 3 + Cosmos | DbtDag từ manifest, mỗi model một task group |

## Lộ trình gợi ý (buổi chiều 4h)

| Tuần | Buổi | Làm gì |
|---|---|---|
| 8 | 1 | Setup, đọc dữ liệu, M1, M2 |
| 8 | 2 | M3, M4 |
| 8 | 3 | M5, M6 |
| 8 | 4 | M7, M8 → `check.py M` xanh 8/8 |
| 8 | 5 | Cube (file 02), viết bài so sánh |
| 9 | 1 | Q1 (+ đi tay ngày 0 → 2 bằng `next` + `run_day.sh`) |
| 9 | 2 | Q2, Q3 |
| 9 | 3 | Q4, Q5, Q6 → `replay.sh` |
| 9 | 4 | Q7, viết runbook cho 6 sự cố |
| 10 | 1 | G1, G2, G3 |
| 10 | 2 | G4, G5, G6 |
| 10 | 3 | O1–O4 (Dagster) |
| 10 | 4 | O5 (Airflow + Cosmos), ADR chọn orchestrator |

Các buổi chiều còn lại: áp dụng sang `adventure_works` (Snowflake) và `thelook` (BigQuery) theo checklist trong [lý thuyết GĐ3](../GD3-ly-thuyet/README.md).

## Quy tắc dùng đáp án

1. Tự làm, chạy `check.py`, đọc thông báo lỗi (nhiều thông báo có sẵn **Gợi ý**), sửa.
2. Bí quá 30 phút thì mở phần **Gợi ý** (thu gọn) trong đề.
3. Chỉ mở `dap-an/` sau khi đã PASS (để so cách làm), hoặc khi đã thử hết gợi ý.

Chạy thử toàn bộ đáp án:

```bash
cp -r lab /tmp/lab-dap-an && cp -r dap-an/* /tmp/lab-dap-an/
cd /tmp/lab-dap-an && export DBT_PROFILES_DIR=. && dbt deps && ./scripts/replay.sh    # 4–5 phút
```

`dap-an/` chứa cả `dbt_project.yml` và `packages.yml` (chép đè lên bản của lab).
