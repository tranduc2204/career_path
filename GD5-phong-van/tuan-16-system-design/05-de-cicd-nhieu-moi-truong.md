# 16.5 Đề 3: Thiết kế CI/CD cho dbt nhiều môi trường

> Nền: GĐ1 tuần 3 (slim CI), GĐ2 tuần 5 (3 môi trường BigQuery, CD khi merge, WIF). Bằng chứng để kể: repo `thelook-analytics`.

## Đề

> *"Chúng tôi có một dbt project 300 model trên Snowflake, 12 người commit. Hiện mọi người chạy `dbt run --target prod` từ máy cá nhân. Tuần trước một người xoá nhầm một cột và 3 dashboard gãy cả buổi sáng. Thiết kế quy trình phát triển và triển khai."*

## Bước 1: Làm rõ

| Câu hỏi | Giả định |
|---|---|
| Git hosting, CI có sẵn? | GitHub + GitHub Actions |
| Bao nhiêu PR/ngày? Thời gian build toàn bộ? | ~15 PR/ngày; full build 40 phút trên warehouse M |
| Có môi trường UAT / nghiệm thu không? | Chưa. Tài chính muốn kiểm số trước khi đổi logic doanh thu |
| Dữ liệu dev lấy từ đâu? | Đọc thẳng prod (rủi ro PII) |
| Có yêu cầu phê duyệt / kiểm toán? | Có với model tài chính |
| Lịch chạy prod? | 06:00 hằng ngày + vài model mỗi giờ |
| dbt Core hay dbt platform? | Core (đề cũng hỏi "nếu dùng platform thì khác gì") |

**Yêu cầu:** (1) không ai chạy prod từ máy cá nhân, (2) thay đổi phá vỡ bị chặn **trước khi merge**, (3) CI nhanh (< 10 phút) và rẻ, (4) Tài chính nghiệm thu được thay đổi logic tiền, (5) rollback trong vài phút, (6) audit: ai đổi gì, khi nào, ai duyệt.

## Bước 2: Ước lượng

Full build 40 phút trên M (4 credit/h) ≈ 2,7 credit. 15 PR × 22 ngày × 2,7 ≈ **890 credit/tháng** nếu CI build toàn bộ (~2.000–3.500 USD). Slim CI (trung bình 10–15 model + con cháu) còn ~5–10% → **< 200 USD/tháng**. Đây là lý do số 1 để làm slim CI, ngoài tốc độ.

## Bước 3: Kiến trúc

```
 ┌────────── DEV ──────────┐    ┌──────────────── CI (mỗi PR) ─────────────────┐    ┌──── UAT (tuỳ chọn) ────┐    ┌──────── PROD ────────┐
 │ schema dbt_<tên người>  │    │ schema ci_pr_<số>                            │    │ schema uat              │    │ schema analytics_*   │
 │ dbt build -s m+         │PR─▶│ 1. lint (sqlfluff), dbt parse, YAML checks   │    │ deploy nhánh release    │    │ deploy khi merge main│
 │ --defer --state prod    │    │ 2. dbt build -s state:modified+              │    │ (hoặc PR gắn nhãn       │    │ (hoặc theo tag)      │
 │ --empty / --sample      │    │    --defer --state <manifest prod>           │    │  "finance-uat")         │    │ job lịch 06:00       │
 │ dữ liệu: prod qua defer │    │ 3. contract / breaking change check          │    │ Tài chính so số với     │    │ lưu artifact (S3)    │
 │ + masking PII           │    │ 4. data diff cho model Tier 1 bị đổi         │    │ prod, ký nghiệm thu     │    │ cảnh báo, freshness  │
 │ role DEV: không ghi prod│    │ 5. comment kết quả lên PR; xoá schema khi đóng│    │                         │    │ role DEPLOY (service)│
 └─────────────────────────┘    └──────────────────────────────────────────────┘    └─────────────────────────┘    └──────────────────────┘
        quyền: chỉ đọc prod             quyền: service account CI                   quyền: UAT                         chỉ CD được ghi
```

Artifact `manifest.json` của prod được CD tải lên object storage sau mỗi lần deploy. CI và dev tải về để `--state`/`--defer`.

## Bước 4: Đi sâu

### 4.1 Môi trường và quyền: chặn "chạy prod từ máy cá nhân"

- Role `DEVELOPER`: đọc prod, ghi `dbt_<tên>`. Không có quyền ghi schema prod. Đây là thay đổi **quan trọng nhất**, làm ngày đầu.
- Service account `CI`: ghi `ci_pr_*`, đọc prod. Service account `DEPLOY`: ghi prod, chỉ dùng trong job CD (bí mật trong GitHub Environments, xác thực bằng key-pair / OIDC, không mật khẩu trong repo).
- `generate_schema_name` theo target: `dev` → `dbt_<user>`, `ci` → `ci_pr_<số>`, `prod` → tên schema thật (GĐ2 tuần 5).
- PII: masking policy ở Snowflake để role DEVELOPER/CI thấy dữ liệu đã che, kể cả khi đọc prod qua defer.

### 4.2 CI nhanh, rẻ và bắt được lỗi thật

```yaml
# .github/workflows/ci.yml (rút gọn)
on: pull_request
jobs:
  ci:
    environment: ci
    steps:
      - uses: actions/checkout@v...
      - run: uv sync --frozen
      - run: sqlfluff lint models --dialect snowflake
      - run: aws s3 cp s3://dbt-artifacts/prod/manifest.json prod-state/manifest.json
      - run: dbt deps && dbt parse --target ci
      - run: dbt build --target ci -s state:modified+ --defer --state prod-state --fail-fast
      - run: python scripts/data_diff_tier1.py --state prod-state      # chỉ model Tier 1 bị đổi
      - run: python scripts/comment_pr.py                             # tóm tắt lên PR
```

| Bắt lỗi | Cơ chế |
|---|---|
| Xoá / đổi kiểu cột của model public (sự cố tuần trước) | **Model contract**: so với `--state`, dbt báo breaking change nếu model có contract bị xoá cột / đổi kiểu mà không tăng version |
| Ai đang dùng model này | `dbt ls -s state:modified+ --resource-type exposure` → liệt kê dashboard bị ảnh hưởng vào comment PR |
| Logic sai | unit test (`test_type:unit`), test dữ liệu trên model bị đổi + con cháu |
| Số thay đổi ngoài ý muốn | Data diff Tier 1: so PR vs prod theo khoá (thêm/mất/đổi) và tổng metric chính |
| SQL bẩn | sqlfluff, pre-commit (dbt-checkpoint: model có description, có test) |
| Cấu hình | `dbt parse` + kiểm tra meta bắt buộc (owner, tier) bằng script đọc manifest |

Mẹo giảm thời gian: `--defer` cho phép không build upstream; model rất lớn thì CI build với `--sample "3 days"` hoặc `--empty` cho phần không cần dữ liệu thật; chạy song song lint và parse; cache `dbt_packages`.

### 4.3 CD: deploy khi merge, artifact, và rollback

Hai lựa chọn:

| | A. Deploy liên tục khi merge `main` | B. Release theo tag (lịch / phê duyệt) |
|---|---|---|
| Tốc độ | Nhanh, mỗi PR lên prod ngay | Chậm hơn, gom thay đổi |
| Rủi ro | Mỗi thay đổi nhỏ, dễ biết lỗi do đâu | Nhiều thay đổi một lần, khó khoanh vùng |
| Hợp | Hầu hết công ty | Ngân hàng / model tài chính cần CAB |

Có thể kết hợp: A cho mọi thứ, B (environment có required reviewers) cho model gắn tag `finance`.

CD job:
1. `dbt build -s state:modified+ --state prod-state` (chỉ build phần đổi, **không** defer: prod phải tự đủ). Model incremental đổi logic thì cân nhắc `--full-refresh` có chủ đích (khai báo trong PR).
2. Upload `manifest.json`, `run_results.json` lên S3 với khoá theo commit SHA (audit + rollback + state cho CI).
3. Thông báo kênh deploy.

**Rollback:**
- Code: revert commit → CD chạy lại. Vài phút với model nhỏ, có thể lâu với model lớn.
- Dữ liệu (nhanh): **blue-green**. Build vào schema mới (`analytics_green`) rồi **swap** (Snowflake `ALTER SCHEMA ... SWAP WITH ...`) hoặc đổi view trỏ tới bảng mới. Rollback = swap lại. `dbt clone` giúp dựng nhanh schema xanh từ bản hiện tại (zero-copy clone) trước khi build phần thay đổi.
- Time travel (Snowflake) / snapshot (BigQuery) để khôi phục bảng bị ghi sai.

### 4.4 UAT cho thay đổi logic tiền

- PR có nhãn `finance-uat` → workflow build phần thay đổi vào schema `uat` (dữ liệu prod, PII che), sinh báo cáo so sánh (data diff tổng doanh thu theo ngày/tháng giữa uat và prod).
- Tài chính duyệt trên PR (required reviewer theo CODEOWNERS cho `models/finance/**`).
- Chỉ merge khi có phê duyệt → đáp ứng audit "ai duyệt".

### 4.5 Thay đổi phá vỡ có kế hoạch: versions

Đổi giao diện model public thì **không sửa tại chỗ**: thêm `v2`, giữ `v1` với `deprecation_date`, thông báo owner của các exposure, theo dõi ai còn ref `v1` (`dbt ls -s dim_x.v1+`), xoá `v1` sau hạn. CI chặn breaking change không có version mới.

## Bước 5: Vận hành

- **Job prod:** orchestrator chạy `dbt build` 06:00 (sau freshness), retry 1 lần cho lỗi tạm thời, `dbt retry` cho lỗi giữa chừng.
- **Giám sát:** thời gian build theo model (xu hướng), chi phí CI/tháng, tỷ lệ PR fail CI, MTTR khi prod lỗi.
- **Vệ sinh:** workflow xoá schema `ci_pr_*` khi PR đóng; xoá schema dev không dùng 30 ngày.

## Nếu dùng dbt platform (Cloud) thì khác gì

Có sẵn: môi trường, job CI theo PR với "defer to production", **state-aware orchestration** (chỉ build model có nguồn/code mới), lưu artifact tự động, IDE, quản lý quyền. Đổi lại phải trả phí theo người dùng / lượt chạy và phụ thuộc nhà cung cấp. Thiết kế logic giống hệt; khác ở chỗ ai vận hành phần "ống nước".

## Câu hỏi đào sâu + ý trả lời

1. **"Defer có rủi ro gì?"** → CI đọc bảng prod cho phần không build. Nếu prod đang hỏng thì CI "xanh nhầm" hoặc "đỏ nhầm". Manifest prod phải mới (lấy từ lần deploy gần nhất). Model đổi tên / đổi schema cần cẩn thận vì ref sẽ trỏ bảng prod cũ.
2. **"Incremental model đổi logic thì CI test thế nào?"** → CI build lần đầu nên chạy như full refresh (bảng chưa có trong schema CI). Phải test thêm nhánh `is_incremental()`: unit test có `overrides: macros: is_incremental: true`, hoặc clone bảng prod vào schema CI (`dbt clone`) rồi chạy incremental lên đó.
3. **"Hai PR cùng sửa một model?"** → Git xử lý xung đột code. Schema CI theo PR tách biệt dữ liệu. Sau khi merge PR đầu, PR thứ hai phải rebase và CI chạy lại với manifest prod mới.
4. **"Làm sao biết thay đổi tốn thêm bao nhiêu tiền?"** → Query tag / job label theo model trong CI. So thời gian và byte quét của model trong CI với lần chạy prod gần nhất, comment lên PR nếu tăng > 30%.
5. **"300 model lên 3.000 model, 5 đội?"** → Slim CI vẫn ổn về thời gian. Thứ vỡ là ownership và tốc độ review → groups + CODEOWNERS, rồi tách **dbt Mesh** (đề 8) để mỗi đội có CI/CD riêng.

## Lỗi hay gặp

- CI build toàn bộ project ("cho chắc"). Chậm, đắt, người ta sẽ bỏ qua CI.
- Không có quyền tách biệt: CI và dev vẫn ghi được prod.
- Quên lưu artifact prod → không có state cho slim CI, không rollback được.
- Rollback bằng "sửa tay bảng prod".
- Không nói gì về PII trong dev/CI.
