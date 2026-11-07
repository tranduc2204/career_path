# 16.8 Đề 6 (Senior): Một project hay nhiều project? Mono-repo hay multi-repo? (dbt Mesh)

> Nền: GĐ3 tuần 10 (groups, access, contracts, versions); GĐ4 tuần 12 (dbt Mesh với `dbt-loom`) nếu bạn đã làm.

## Đề

> *"Chúng tôi có một dbt project 1.200 model, 25 người, 5 đội. CI mất 35 phút dù có slim CI, PR chờ review lâu, một đội sửa làm hỏng model của đội khác mỗi tuần. Có nên tách project không? Tách thế nào?"*

## Phân biệt 2 câu hỏi hay bị trộn lẫn

| Câu hỏi | Các lựa chọn |
|---|---|
| **Bao nhiêu dbt project?** | 1 project lớn ↔ nhiều project (Mesh: project ref chéo qua model public) |
| **Bao nhiêu git repo?** | Mono-repo (nhiều project trong 1 repo) ↔ multi-repo (mỗi project 1 repo) |

Có 4 tổ hợp. Phổ biến nhất khi mới tách: **nhiều project trong mono-repo**.

## Triệu chứng nào thật sự cần tách

| Triệu chứng | Tách project có giải quyết? | Cách khác rẻ hơn |
|---|---|---|
| Đội này làm hỏng model đội kia | ✅ (ranh giới cứng) | groups + `access: private` + contract + CODEOWNERS (thử trước) |
| CI chậm | Một phần | slim CI, defer, `--empty`, chia job song song |
| `dbt parse` chậm, IDE ì | ✅ | partial parsing, bớt macro nặng |
| Đội cần nhịp deploy khác nhau (finance theo tháng, product hằng giờ) | ✅ | job theo selector/tag |
| Quyền truy cập code/dữ liệu khác nhau (risk không muốn ai đọc code) | ✅ (multi-repo) | khó trong 1 repo |
| Nhiều nền tảng (Snowflake + Databricks) | ✅ | không |

Nguyên tắc: **dùng governance trong một project trước**. Tách khi ranh giới domain đã ổn định và giao diện (model public) đã rõ. Tách quá sớm thì đổi một vấn đề tổ chức thành vấn đề phụ thuộc giữa các repo.

## Thiết kế khi đã quyết định tách

```
mono-repo: analytics/
├── projects/
│   ├── platform/      ← staging dùng chung, dim_date, dim_customer (public, contract, version)
│   ├── finance/       ← ref('platform', 'dim_customer')   — chỉ model PUBLIC
│   ├── marketing/
│   └── risk/
├── packages/          ← macro dùng chung (package nội bộ), linting config
└── .github/workflows/ ← CI theo đường dẫn thay đổi (paths filter)
```

| Quyết định | Lựa chọn và lý do |
|---|---|
| **Ranh giới** | Theo domain nghiệp vụ và theo đội sở hữu (Conway). Không tách theo tầng (một project staging, một project marts) vì sẽ tạo phụ thuộc vòng về tổ chức |
| **Giao diện** | Chỉ model `public` + contract được ref chéo; thay đổi phá vỡ phải có version mới + `deprecation_date` |
| **Ref chéo** | dbt platform: cross-project ref có sẵn. dbt Core: plugin `dbt-loom` đọc manifest của project upstream (từ file / S3 / dbt platform) |
| **Phụ thuộc vòng** | Cấm. A ref B thì B không ref A. Cần "dữ liệu ngược chiều" → tách model ra project thứ ba (platform) |
| **Macro dùng chung** | Package nội bộ có version (git tag), không copy-paste |
| **CI** | Mỗi project CI riêng, chỉ chạy khi thư mục đổi; **CI của project upstream kiểm tra cả downstream**: đổi model public thì chạy test/parse của các project con (hoặc ít nhất kiểm contract + version) |
| **Orchestration** | Project downstream chạy khi model public upstream đã cập nhật (asset-aware: Dagster / dbt platform / Airflow Assets) |
| **Mono hay multi-repo** | Mono-repo khi các đội cùng tổ chức, muốn thay đổi xuyên project trong một PR, tooling chung. Multi-repo khi cần quyền riêng, vòng đời phát hành độc lập, hoặc đội ở công ty con |

## Kế hoạch chuyển đổi

1. Gán groups + access cho project hiện tại, sửa mọi vi phạm (như bài G2 của lab GĐ3). **Bước này đã giải quyết được 50% vấn đề.**
2. Xác định model public cho từng domain, thêm contract.
3. Tách **một** domain ít phụ thuộc nhất ra project riêng (thường là một domain lá như marketing), chạy song song, đo lại CI và tần suất sự cố.
4. Tách dần, `platform` cuối cùng.

## Đánh đổi phải nói ra

- **Mất:** refactor xuyên domain trong một PR khó hơn; tìm lineage toàn cục cần catalog; nhiều CI/CD để vận hành; phiên bản dbt/packages giữa các project phải đồng bộ.
- **Được:** ranh giới sở hữu rõ, CI nhanh hơn theo project, deploy độc lập, quyền truy cập theo project.

## Câu trả lời 2 phút

> *"Em chưa tách ngay. Đầu tiên em áp groups, private access, contract và CODEOWNERS trong project hiện tại, vì việc đội này làm hỏng đội kia là vấn đề ranh giới, và governance trong một project giải quyết được phần lớn. Song song, em đo lại CI và tìm xem model nào thật sự là giao diện giữa các đội. Khi ranh giới ổn định, em tách theo domain thành nhiều project trong một mono-repo, ref chéo chỉ qua model public có contract và version, macro chung thành package nội bộ, CI theo thư mục. Em sẽ chuyển sang multi-repo chỉ khi có yêu cầu quyền truy cập hoặc nhịp phát hành độc lập thật sự."*
