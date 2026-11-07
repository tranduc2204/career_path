# 03 — Data quality framework (Q1–Q7)

> Lý thuyết: [GD3-ly-thuyet/tuan-9](../../GD3-ly-thuyet/README.md#tuần-9-1012--1612--data-quality-framework). Chấm: `./scripts/replay.sh` (ngày 0 → 7, ~4 phút), rồi `check.py Q` đọc kết quả từng ngày trong `.replay/`.

Mục tiêu của tuần này **không phải viết nhiều test**. Mục tiêu là thiết kế một bộ giám sát mà:

1. **Bắt được** 6 sự cố trong [dòng thời gian](00-setup.md#5-dòng-thời-gian-8-ngày-6-sự-cố), **đúng ngày**;
2. **Im lặng** vào ngày bình thường. Một hệ thống báo động giả 3 lần/tuần sẽ bị cả team tắt thông báo, và đó là lúc sự cố thật lọt qua;
3. Phản ứng **đúng mức**: lỗi làm sai số thì chặn (`error`), thay đổi nghiệp vụ thì cảnh báo (`warn`), còn pipeline thì vẫn chạy được.

`check.py` chấm theo nguyên tắc: *có ít nhất một test (cùng một test) bật vào tất cả ngày có sự cố và `pass` vào các ngày được chỉ định là sạch*. Test "lúc nào cũng đỏ" không được tính.

## Chuẩn bị: cài Elementary

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.3.0", "<2.0.0"]
  - package: elementary-data/elementary
    version: 0.26.1
```

```bash
dbt deps
dbt run -s elementary      # tạo các bảng hệ thống trong schema dev_elementary (dbt_project.yml đã cấu hình)
```

Elementary có bản hỗ trợ DuckDB (đã chạy thử trên 0.26.1). Test của Elementary gọi như generic test thường: `elementary.volume_anomalies`, `elementary.column_anomalies`, `elementary.schema_changes`... Tham số đặt trong `arguments:` (dbt ≥ 1.10), cấu hình (severity, tags) trong `config:`.

Bạn có thể gắn test vào **source** (`models/staging/_sources.yml`) hoặc vào model. Câu hỏi thiết kế: chỗ nào bắt sớm nhất, chỗ nào chặn đúng phần cần chặn?

---

## Q1 ⭐⭐⭐ — Freshness theo SLA, không báo động giả

SLA của team (đưa vào `_sources.yml`):

| Nguồn | SLA |
|---|---|
| `shop.orders`, `shop.order_items`, `crm.customers`, `web.sessions`, `mkt.ad_spend` | **warn** nếu dữ liệu mới nhất cũ hơn **12 giờ**, **error** nếu cũ hơn **36 giờ** |
| `shop.refunds`, `erp.products` | Phải được theo dõi (có trong kết quả `dbt source freshness`), cùng ngưỡng 12h/36h, nhưng **không được báo động giả** |

`check.py` yêu cầu:

- `mkt.ad_spend`: ngày 0–3 `pass`, ngày 4 `warn`, ngày 5–6 `error`, ngày 7 `pass`;
- 6 nguồn còn lại `pass` **mọi ngày**.

Bắt đầu bằng cách đơn giản nhất (`loaded_at_field: _loaded_at` cho tất cả), chạy `replay.sh`, xem nguồn nào đỏ vào ngày nào và tại sao.

<details><summary>Gợi ý 1</summary>

`erp.products` gần như không bao giờ có dòng mới, và `shop.refunds` có ngày không có hoàn tiền nào. Dữ liệu "cũ" nhưng **connector vẫn chạy bình thường**. Câu hỏi thật của SLA là "connector có chạy không", vậy đo bằng thứ gì?
</details>

<details><summary>Gợi ý 2</summary>

dbt ≥ 1.10 có `loaded_at_query`: một câu SQL trả về thời điểm "nạp gần nhất". `ingest.sync_log` ghi mỗi lần connector chạy thành công, kể cả khi 0 dòng mới. Nhớ lọc `status = 'success'`: ngày 4–6 connector mkt chạy nhưng lỗi.

```yaml
      - name: refunds
        config:
          loaded_at_query: >
            select max(synced_at) from {{ source('ingest', 'sync_log') }}
            where table_name = 'shop.refunds' and status = 'success'
```
</details>

## Q2 ⭐⭐⭐ — Volume anomaly: connector nạp thiếu

Ngày 2 chỉ về ~30% số đơn. Không có test "luật" nào bắt được chuyện này: mọi đơn về đều hợp lệ, chỉ là **thiếu**. Dùng `elementary.volume_anomalies` trên đơn hàng, theo thời gian đặt đơn (`timestamp_column`), bucket theo ngày.

Yêu cầu: bật ngày **2**, `pass` ngày **0, 1, 3** (ngày 3 phần còn lại đã về). Dùng `severity: warn`: anomaly detection là thống kê, có xác suất sai. Hãy nghĩ xem có nên để nó chặn cả pipeline không.

Tham số cần hiểu: `training_period`, `detection_period`, `time_bucket`, `anomaly_direction`, `anomaly_sensitivity`, `seasonality`.

<details><summary>Gợi ý: test có mà không bao giờ bật?</summary>

```sql
select detected_at, status, test_results_description
from dev_elementary.elementary_test_results
where test_type = 'anomaly_detection' order by detected_at;
```

Câu mô tả có dạng *"The last row_count value is 32. The average for this metric is …"*. Nếu "average" thấp vô lý (vd ~33 đơn/ngày trong khi thực tế ~120), cửa sổ huấn luyện đang chứa những ngày **chưa có dữ liệu** (bucket = 0). Lab chỉ có 60 ngày lịch sử. `seasonality: day_of_week` làm Elementary so với cùng thứ trong một khoảng **dài gấp nhiều lần** `training_period`. Đã đo trên lab: bật seasonality thì trung bình còn ~33 và ngày 2 không bị phát hiện.
</details>

## Q3 ⭐⭐⭐ — Null spike trên cột được phép NULL

`web.sessions.customer_id` NULL ~40% là bình thường (khách chưa đăng nhập). Ngày 3, lỗi tracking làm ~90% phiên mất customer_id.

Yêu cầu: bật ngày **3**, `pass` ngày **0, 1, 2, 7**. Ngày 4 bật hay không tuỳ `detection_period` của bạn. **Không** được có test `not_null` trên cột này.

Trước khi làm, thử thêm `not_null` vào cột đó rồi `dbt build`: chuyện gì xảy ra với `stg_web__sessions` và `fct_sessions`? Đó là lý do Q7 cũng sẽ đỏ.

## Q4 ⭐⭐ — Giá trị mới: cảnh báo, không chặn

Ngày 4 website mở phương thức thanh toán `bnpl`. Viết `accepted_values` cho `payment_method` với 4 giá trị đang có (`cod, card, ewallet, bank_transfer`). Yêu cầu: `pass` ngày 0–3, **`warn`** ngày 4–7. Nếu là `fail` (`severity: error`) thì `fct_orders` và mọi thứ phía sau bị skip vì một thay đổi **hợp lệ** của nghiệp vụ.

Sau khi PASS, nghĩ quy trình: ai nhận cảnh báo này, ai quyết định thêm `bnpl` vào danh sách, và semantic layer có cần sửa gì không?

## Q5 ⭐⭐⭐⭐ — Đổi tên cột ở nguồn

Ngày 5 CRM đổi `phone` → `phone_number`. Model `stg_crm__customers` dựng sẵn đang `select phone` → **lỗi**, kéo theo `dim_customers` và mọi thứ phía sau.

Yêu cầu:

1. Một test `elementary.schema_changes` trên `crm.customers` (hoặc staging) bật ngày **5** và `pass` ngày **3, 4**;
2. `stg_crm__customers` build **thành công mọi ngày 0–7**. Khi `replay.sh` chạy, model của bạn gặp cả schema cũ (ngày 0–4) lẫn mới (ngày 5–7), nên phải tự nhận ra cột nào đang có;
3. Ở ngày 7, `stg_crm__customers.phone` có giá trị cho ≥ 95% khách.

<details><summary>Gợi ý</summary>

```sql
{%- set src = source('crm', 'customers') -%}
{%- set cols = [] -%}
{%- if execute -%}
  {%- set cols = adapter.get_columns_in_relation(src) | map(attribute='name') | map('lower') | list -%}
{%- endif -%}
{%- set phone_col = 'phone_number' if 'phone_number' in cols else 'phone' %}
```

Cẩn thận với `-%}` ngay trước một dòng comment SQL `--`: dấu `-` ăn mất xuống dòng, comment dính vào dòng `select` và nuốt luôn nó. Dùng comment Jinja `{# #}`.
</details>

Đây là "phòng thủ ở staging". Cách bền hơn là **data contract với đội CRM**: họ báo trước khi đổi schema, hoặc giữ cột cũ một thời gian. Viết 3 dòng vào runbook về việc bạn sẽ đề xuất gì với đội CRM.

## Q6 ⭐⭐⭐ — Đơn giá sai đơn vị: chặn trước khi lên dashboard

Ngày 6, đơn kênh app ghi `unit_price` theo nghìn đồng. Doanh thu ngày 06/12 tụt mạnh **nhưng mọi dòng đều "hợp lệ"** về kiểu dữ liệu. Ngày 7 đội app restate lại giá đúng.

Yêu cầu:

1. Một test trên `unit_price` (source / `stg_shop__order_items` / `fct_order_items`) **fail** ngày **6**, `pass` mọi ngày khác;
2. Ngày 6, `fct_order_items` **không được build** với số sai. Dashboard nên giữ số hôm qua (đúng) còn hơn hiện số hôm nay (sai).

Mây Shop không bán món nào dưới 1.000đ. Đây là **luật nghiệp vụ biết trước**, nên một test luật (`dbt_utils.accepted_range`, `expression_is_true`) rẻ, chắc chắn và dễ giải thích hơn anomaly detection.

## Q7 ⭐⭐ — Không báo động giả

Ngày **0, 1, 7** là ngày sạch: không test nào `fail`/`error`, không nguồn nào freshness khác `pass`. Mọi ngày: không model nào `error` (bị `skip` vì test chặn thì được, đó là chủ ý ở Q6).

`warn` của Q4 vẫn được phép vào ngày 7. Đó là cảnh báo đang mở, chờ người xử lý.

---

## Runbook (không chấm, nhưng là sản phẩm chính của tuần)

Viết `docs/incident-runbook.md` cho `adventure_works` hoặc `thelook`, dùng 6 sự cố của lab làm ví dụ. Mẫu trong [GD3-ly-thuyet/tuan-9/05-incident-runbook.md](../../GD3-ly-thuyet/tuan-9/05-incident-runbook.md). Với mỗi loại tín hiệu (freshness, volume, null, giá trị mới, schema, luật nghiệp vụ):

- Ai nhận cảnh báo, qua kênh nào, mức độ (SEV1–3)
- 3 câu lệnh/truy vấn đầu tiên để chẩn đoán
- Cách khắc phục tạm và cách sửa gốc
- Cần backfill không? Báo cho người dùng dashboard thế nào?

## Áp dụng vào project thật

- `thelook` hoặc `adventure_works`: SLA freshness cho mọi source, `volume_anomalies` cho 2 fact chính, `schema_changes` cho source quan trọng, `edr report` (cần `pip install 'elementary-data[bigquery]'` hoặc `[snowflake]`) rồi chụp ảnh đưa vào README.
- Mỗi mart public ghi `meta: {sla: "06:30 hằng ngày", owner: ...}` để người dùng biết cam kết.

## Câu hỏi tự kiểm tra

1. Freshness "dữ liệu mới nhất" và "connector chạy lần cuối" khác nhau thế nào? Khi nào dùng cái nào?
2. Vì sao test trên **source** bị lỗi lại làm skip các model phía sau trong `dbt build`? Nếu không muốn thế thì làm gì?
3. `detection_period` dài 2 ngày thì sự cố ngày 3 còn làm đỏ đến ngày nào? Đánh đổi gì nếu đặt 1 ngày?
4. Liệt kê 3 tình huống anomaly detection tốt hơn test luật, và 3 tình huống ngược lại.
