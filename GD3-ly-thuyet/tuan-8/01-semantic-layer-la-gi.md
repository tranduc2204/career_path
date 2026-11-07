# 8.1 Semantic layer là gì và vì sao AE Mid phải biết

## Vấn đề: cùng một con số, năm định nghĩa

Thứ Hai, ban giám đốc Mây Shop thấy 3 con số "doanh thu tháng 11":

| Ai | Số | Cách tính |
|---|---|---|
| Dashboard Finance (Metabase) | 10,08 tỷ | tổng tiền hàng, bỏ đơn huỷ, theo ngày đặt |
| Báo cáo Marketing (Google Sheets) | 10,41 tỷ | tổng tiền hàng **gồm** đơn huỷ (lấy từ export) |
| Notebook của Data Science | 10,62 tỷ | `total_amount` (gồm phí ship), theo ngày **giao** |

Không ai sai về SQL. Họ sai vì **định nghĩa metric nằm rải rác** trong từng dashboard, notebook, file Excel. Hiện tượng này gọi là *metric drift* hay *metric inconsistency*. Bảng mart sạch (GĐ1–GĐ2) là điều kiện cần, chưa đủ: mart cho bạn *dữ liệu đúng*, nhưng mỗi người vẫn tự viết `SUM`, `COUNT DISTINCT`, `WHERE` theo kiểu của mình.

**Semantic layer** là tầng nằm giữa mart và công cụ tiêu thụ (BI, notebook, API, trợ lý AI). Mỗi metric được định nghĩa **một lần**, bằng code, có review và version. Mọi công cụ hỏi tầng này *"revenue theo kênh, theo tuần"* thay vì tự viết SQL.

```
  nguồn ──▶ staging ──▶ marts ──▶ SEMANTIC LAYER ──▶ BI / notebook / API / AI agent
                                  │ entity, dimension, metric
                                  │ tự sinh SQL đúng grain, đúng join
                                  └ một định nghĩa, nhiều nơi dùng
```

## Semantic layer làm được gì mà bảng mart tổng hợp sẵn không làm được

Cách "cũ": tạo sẵn `agg_revenue_daily_by_channel`, `agg_revenue_monthly_by_category`... Mỗi câu hỏi mới lại cần một bảng mới. Bùng nổ tổ hợp (*combinatorial explosion*): 15 metric × 8 dimension × 4 grain thời gian là hàng trăm bảng.

| Năng lực | Bảng tổng hợp sẵn | Semantic layer |
|---|---|---|
| Đúng ở mọi grain | ❌ AOV ngày không cộng lên AOV tháng được | ✅ ratio tính lại từ tử và mẫu ở grain được hỏi |
| Distinct đúng | ❌ cộng `buyers` theo ngày ra số sai cho tuần | ✅ `count_distinct` tính lại trong cửa sổ |
| Join an toàn | tuỳ người viết | ✅ biết grain từng bảng, chặn fan-out |
| Thêm dimension | sửa model, chạy lại | khai báo, có ngay |
| Một nguồn sự thật | không | có, metric là code |

Trong lab bạn sẽ thấy cả ba: `aov` tháng ≠ trung bình `aov` ngày, `buyers_7d` ≠ tổng `buyers` 7 ngày, và `roas` ghép 2 fact khác grain mà không fan-out.

## Các họ semantic layer (2026)

| Họ | Ví dụ | Đặc điểm |
|---|---|---|
| Gắn với transformation | **dbt Semantic Layer (MetricFlow)** | Định nghĩa cạnh model dbt, cùng repo, cùng CI. Truy vấn qua `mf` (Core) hoặc API JDBC/GraphQL (dbt platform) |
| Độc lập ("headless BI") | **Cube**, AtScale | Server riêng, có cache/pre-aggregation, REST/GraphQL/SQL API, phân quyền theo hàng |
| Gắn với BI | LookML (Looker), Power BI semantic model, Tableau | Mạnh trong hệ sinh thái của mình, khó dùng lại ngoài BI đó |
| Gắn với warehouse | Snowflake semantic views, Databricks metric views | Định nghĩa ngay trong warehouse, dùng được từ SQL |

Năm 2025 nhiều nhà cung cấp (dbt Labs, Snowflake, Salesforce/Tableau...) lập nhóm **Open Semantic Interchange (OSI)** để chuẩn hoá cách mô tả metric giữa các công cụ. Trong lab, `dbt parse` của dbt-core 1.12 sinh thêm `target/osi_document.json` và in cảnh báo cho những metric chưa biểu diễn được bằng OSI (cumulative, conversion). Bạn chưa cần dùng file này. Biết là nó tồn tại và đang phát triển là đủ.

## MetricFlow trong dbt: các khái niệm

```
semantic model  = 1 model dbt + mô tả ngữ nghĩa
  ├── entity     = khoá để nối (primary / unique / foreign / natural)
  ├── dimension  = cột để group/filter (categorical / time)
  └── metric     = phép tính có tên (simple / ratio / derived / cumulative / conversion)
time spine      = bảng ngày liên tục, dùng cho cumulative, offset, lấp ngày trống
saved query     = truy vấn đặt tên sẵn (metric + group by + filter)
```

Điểm khác biệt quan trọng của MetricFlow: bạn **không khai báo đường join**. Bạn chỉ khai báo entity. MetricFlow tự tìm đường nối giữa các semantic model qua entity cùng tên, và **từ chối** những join có thể nhân dòng (fan-out). Chi tiết ở 8.2.

## Cách MetricFlow sinh SQL (đọc `--explain` một lần cho quen)

```bash
mf query --metrics revenue,orders --group-by metric_time__day,sales_order__channel --explain
```

Đại ý SQL sinh ra:

1. Với **mỗi metric**, đọc semantic model chứa nó, join (LEFT) tới các semantic model cần cho dimension/filter, lọc, `GROUP BY` ở grain được hỏi.
2. Các metric từ semantic model khác nhau được tính **riêng**, rồi `FULL OUTER JOIN` theo các cột group-by.
3. Ratio/derived tính **sau cùng**, trên kết quả đã tổng hợp.

Bước 2 là lý do `revenue` (từ dòng hàng) và `orders` (từ đơn) đứng chung một bảng kết quả mà không bị nhân dòng: không bao giờ có chuyện join `fct_order_items` với `fct_orders` rồi mới `COUNT`.

## Khi nào chưa cần semantic layer

- Một đội, 1–2 dashboard, ít người hỏi số: một bảng mart + tài liệu là đủ.
- BI hiện tại (Looker) đã là nguồn định nghĩa duy nhất và mọi người chỉ dùng nó.
- Đội chưa có mart ổn định. Semantic layer trên mart lộn xộn chỉ làm sự lộn xộn chạy nhanh hơn.

Semantic layer đáng làm khi: nhiều công cụ tiêu thụ, nhiều đội định nghĩa cùng metric, hoặc có **trợ lý AI** cần hỏi số. LLM tự viết SQL trên 300 bảng thì sai rất nhiều. Hỏi qua metric đã định nghĩa thì đúng hơn hẳn. Đây là đề tài tuần 14 (AI context layer).

## Câu hỏi tự kiểm tra

1. Giải thích "metric drift" cho một người không làm dữ liệu, kèm ví dụ.
2. Vì sao bảng `agg_daily` có cột `aov` không thể dùng để báo cáo AOV tháng?
3. MetricFlow tính `revenue` và `orders` trong cùng một truy vấn bằng cách nào mà không fan-out?
4. Kể 2 tình huống công ty bạn **không nên** đầu tư semantic layer lúc này.

## Tài liệu

- dbt docs: *About MetricFlow*, *Semantic models*, *Metrics overview*
- dbt Developer Blog: *How to design and structure dbt metrics*
- Benn Stancil, *The missing piece of the modern data stack* (2021), bài khởi đầu cuộc tranh luận về metrics layer
