# Bước 6 — Tự kiểm tra và đưa vào portfolio

## Checklist cuối tuần 5

### Hạ tầng
- [ ] 2 (hoặc 3) project GCP, dataset ở location `US`, budget alert, quota query/ngày
- [ ] `sa-dbt-ci` và `sa-dbt-prod`, quyền tối thiểu, **không có key JSON nào** tồn tại (`gcloud iam service-accounts keys list --iam-account=<email> --managed-by=user` trả về rỗng)
- [ ] WIF: provider có attribute condition; prod chỉ nhận token của environment `production`

### dbt
- [ ] 3 target, `generate_schema_name` cho tên dataset theo môi trường
- [ ] `maximum_bytes_billed` cho cả 3 target
- [ ] Dev giới hạn dữ liệu (`limit_in_dev` hoặc `--sample`)
- [ ] Staging 7 bảng, marts theo bus matrix, test unique trên grain mọi fact
- [ ] Job label (`query-comment` + `job-label: true`)

### CI/CD
- [ ] CI: lint + slim CI + defer, dataset riêng mỗi PR
- [ ] CD: deploy khi merge, build đủ hằng ngày, manifest lên GCS chỉ khi thành công
- [ ] Cleanup khi PR đóng
- [ ] Branch protection + environment `production` chỉ cho `main`

### Tài liệu
- [ ] README (mục dưới)
- [ ] `docs/adr/0002-moi-truong-va-cd.md`

## README của repo nên có

1. **Một câu**: project làm gì, trên dữ liệu nào.
2. **Sơ đồ kiến trúc** (vẽ lại sơ đồ ở README của bộ hướng dẫn này, thêm tên project thật).
3. **Bus matrix** + grain từng fact.
4. **Môi trường**: bảng dev/ci/prod (project, dataset, ai chạy, xác thực bằng gì).
5. **Vòng đời một thay đổi**: ảnh chụp PR → CI xanh → merge → CD → dataset PR bị xoá.
6. **Chi phí**: số liệu thật (vd "CI mỗi PR ~20 MB, prod hằng ngày ~300 MB, cả tháng < 1 TiB miễn phí") + rào chắn đang bật.
7. **Cách chạy trên máy** (3–5 lệnh).
8. Link ADR.

## Câu nói phỏng vấn (luyện 60 giây)

> "Project 2 của em chạy trên BigQuery với 3 môi trường. Dev là dataset riêng của em, giới hạn 90 ngày dữ liệu. Mỗi PR có dataset riêng, CI chỉ build các model thay đổi và đọc phần còn lại từ prod qua `--defer`. Merge vào main thì GitHub Actions tự deploy prod, rồi lưu manifest lên GCS làm chuẩn so sánh cho PR sau. Xác thực bằng Workload Identity Federation nên không có key nào; service account prod chỉ cấp được cho job chạy trong environment production, mà environment đó chỉ cho nhánh main. Mọi query có label theo model nên em biết model nào tốn bao nhiêu tiền."

## Bước tiếp theo

Tuần 7 dùng chính project này cho phần BigQuery của performance playbook: [bai-tap-performance](../../bai-tap-performance/README.md).
